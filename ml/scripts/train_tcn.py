#!/usr/bin/env python3
"""Train and compare the phase-3 7-variable TCN without materializing all windows."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oilwell_ml.tcn import TCNConfig, build_tcn, parameter_count, preferred_device
from oilwell_ml.tcn_data import StreamingWindowDataset, fit_scaler, iter_windows

TARGETS = {0: "Normal", 3: "Severe Slugging", 4: "Flow Instability", 9: "Hydrate in Service Line"}


def commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def evaluate(model, loader, device, torch_module) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    expected, predicted = [], []
    with torch_module.no_grad():
        for inputs, labels in loader:
            output = model(inputs.to(device)).argmax(dim=1).cpu().numpy()
            predicted.extend(output.tolist())
            expected.extend(labels.numpy().tolist())
    return np.asarray(expected), np.asarray(predicted)


def report(expected: np.ndarray, predicted: np.ndarray, labels: list[int]) -> dict:
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support

    precision, recall, f1, _ = precision_recall_fscore_support(expected, predicted, labels=labels, zero_division=0)
    return {
        "accuracy": float(accuracy_score(expected, predicted)),
        "macro_precision": float(np.mean(precision)), "macro_recall": float(np.mean(recall)), "macro_f1": float(np.mean(f1)),
        "per_class_recall": {str(label): float(value) for label, value in zip(labels, recall)},
        "confusion_matrix": confusion_matrix(expected, predicted, labels=labels).tolist(),
        "classification_report": classification_report(expected, predicted, labels=labels, zero_division=0, output_dict=True),
    }


parser = argparse.ArgumentParser()
parser.add_argument("selection", type=Path)
parser.add_argument("--data-root", type=Path, required=True)
parser.add_argument("--split", type=Path, default=Path("docs/experiments/3w-split.json"))
parser.add_argument("--artifacts", type=Path, default=Path("ml/artifacts/tcn-shadow"))
parser.add_argument("--xgb-metrics", type=Path, default=Path("ml/artifacts/current/metrics.json"))
parser.add_argument("--epochs", type=int, default=30)
parser.add_argument("--patience", type=int, default=5)
parser.add_argument("--batch-size", type=int, default=32)
parser.add_argument("--seed", type=int, default=20260910)
args = parser.parse_args()

import torch
from torch.utils.data import DataLoader

torch.manual_seed(args.seed); np.random.seed(args.seed); random.seed(args.seed)
selection, split = json.loads(args.selection.read_text()), json.loads(args.split.read_text())
if "groups" not in split:
    raise ValueError("split manifest must contain grouped train/validation/test assignments")
by_group = {str(item.get("well_id") or item["instance_id"]): item for item in selection["instances"]}
groups = split["groups"]
if set().union(*[set(groups[name]) for name in ("train", "validation", "test")]) - set(by_group):
    raise ValueError("split manifest references an instance not present in selection")
sets = {name: [by_group[group] for group in groups[name]] for name in ("train", "validation", "test")}
if not all(sets.values()):
    raise ValueError("TCN requires non-empty train, validation and test group sets")
scaler = fit_scaler(sets["train"], args.data_root)
datasets = {name: StreamingWindowDataset(items, args.data_root, scaler) for name, items in sets.items()}
loaders = {name: DataLoader(dataset, batch_size=args.batch_size) for name, dataset in datasets.items()}
label_to_index = {label: index for index, label in enumerate(TARGETS)}
counts = Counter(label for _, label in iter_windows(sets["train"], args.data_root))
if set(counts) != set(TARGETS):
    raise ValueError("every target class needs at least one training window")
weights = torch.tensor([sum(counts.values()) / (len(TARGETS) * counts[label]) for label in TARGETS], dtype=torch.float32)
config = TCNConfig(); model = build_tcn(config)
if parameter_count(model) > 1_000_000:
    raise ValueError("TCN exceeds the 1,000,000 parameter limit")
device = preferred_device(torch); model.to(device)
criterion = torch.nn.CrossEntropyLoss(weight=weights.to(device)); optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
best_f1, stale, best_state = -1.0, 0, None
for epoch in range(1, args.epochs + 1):
    model.train()
    for inputs, labels in loaders["train"]:
        optimizer.zero_grad(); loss = criterion(model(inputs.to(device)), torch.tensor([label_to_index[int(label)] for label in labels], device=device))
        loss.backward(); optimizer.step()
    validation_expected, validation_predicted = evaluate(model, loaders["validation"], device, torch)
    validation_expected = np.asarray([label_to_index[int(label)] for label in validation_expected])
    validation_labels = [label_to_index[label] for label in TARGETS]
    score = report(validation_expected, validation_predicted, validation_labels)["macro_f1"]
    if score > best_f1:
        best_f1, stale = score, 0
        best_state = {name: value.detach().cpu() for name, value in model.state_dict().items()}
    else:
        stale += 1
        if stale >= args.patience:
            break
if best_state is None:
    raise RuntimeError("training did not produce a checkpoint")
model.load_state_dict(best_state); model.to("cpu")
test_expected, test_predicted = evaluate(model, loaders["test"], torch.device("cpu"), torch)
test_expected = np.asarray([label_to_index[int(label)] for label in test_expected])
labels = [label_to_index[label] for label in TARGETS]
metrics = report(test_expected, test_predicted, labels)
started = perf_counter()
with torch.no_grad():
    for inputs, _ in loaders["test"]:
        model(inputs)
metrics["cpu_inference_latency_ms_per_window"] = (perf_counter() - started) * 1000 / max(len(test_expected), 1)
metrics["source_label_mapping"] = {str(index): str(label) for label, index in label_to_index.items()}
args.artifacts.mkdir(parents=True, exist_ok=True)
torch.save(model.state_dict(), args.artifacts / "tcn_model.pt")
(args.artifacts / "tcn_config.json").write_text(json.dumps(config.to_dict(), indent=2) + "\n")
(args.artifacts / "scaler.json").write_text(json.dumps(scaler.to_dict(), indent=2) + "\n")
split_sha = hashlib.sha256(args.split.read_bytes()).hexdigest()
metadata = {
    "version": datetime.now(UTC).strftime("tcn-%Y%m%dT%H%M%SZ"), "model_type": "tcn", "mode": "shadow",
    "training_data_version": "Petrobras 3W Dataset 2.0.0", "features": ["P_PDG", "P_TPT", "T_TPT", "P_MON_CKP", "T_JUS_CKP", "P_JUS_CKGL", "QGL"],
    "window_seconds": 180, "stride_seconds": 10, "class_mapping": {str(index): name for index, name in enumerate(TARGETS.values())},
    "metrics": metrics, "created_at": datetime.now(UTC).isoformat(), "git_commit": commit(), "artifact_file": "tcn_model.pt",
    "feature_schema_version": "3w-7v-tcn-v1", "manifest_sha256": hashlib.sha256(args.selection.read_bytes()).hexdigest(),
    "split_sha256": split_sha, "parameters": {"epochs_requested": args.epochs, "early_stopping_patience": args.patience, "batch_size": args.batch_size, "seed": args.seed, "device": str(device), "best_validation_macro_f1": best_f1, "parameter_count": parameter_count(model)},
    "config_file": "tcn_config.json", "scaler_file": "scaler.json",
}
(args.artifacts / "model_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
xgb = json.loads(args.xgb_metrics.read_text()) if args.xgb_metrics.exists() else {}
comparison = {"same_split_sha256": split_sha, "tcn": metrics, "xgboost": xgb.get("xgboost"), "note": "Both models must use the split recorded above; train TCN only after baseline split generation."}
(args.artifacts / "comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n")
print(f"Wrote TCN shadow artifact to {args.artifacts}; test Macro F1={metrics['macro_f1']:.4f}")
