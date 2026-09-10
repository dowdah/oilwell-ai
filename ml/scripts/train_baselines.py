#!/usr/bin/env python3
"""Train Isolation Forest and XGBoost from a selected 3W instance table."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import pyarrow.parquet as pq
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from xgboost import XGBClassifier

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oilwell_ml.features import CORE_VARIABLES, FEATURE_NAMES, window_features
from oilwell_ml.manifest import VARIABLE_ALIASES
from oilwell_ml.split import grouped_split

TARGETS = {"0": "Normal", "3": "Severe Slugging", "4": "Flow Instability", "9": "Hydrate in Service Line"}


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def stream_windows(path: Path, window_size: int = 180, stride: int = 10):
    parquet = pq.ParquetFile(path)
    columns = set(parquet.schema.names)
    mapping = {target: next((name for name in aliases if name in columns), None) for target, aliases in VARIABLE_ALIASES.items()}
    missing = [name for name, source in mapping.items() if source is None]
    if missing:
        raise ValueError(f"{path.name} is missing required variables: {', '.join(missing)}")
    rows: deque[dict[str, float]] = deque(maxlen=window_size)
    index = 0
    for batch in parquet.iter_batches(batch_size=4096, columns=list(mapping.values())):
        for row in batch.to_pylist():
            if any(row[source] is None for source in mapping.values()):
                continue
            rows.append({target: float(row[source]) for target, source in mapping.items()})
            index += 1
            if len(rows) == window_size and (index - window_size) % stride == 0:
                yield window_features(list(rows))


def features_for_groups(items: list[dict], data_root: Path) -> tuple[np.ndarray, np.ndarray]:
    features, labels = [], []
    code_to_index = {code: index for index, code in enumerate(TARGETS)}
    for item in items:
        for feature_row in stream_windows(data_root / item["source_path"]):
            features.append(feature_row)
            labels.append(code_to_index[item["label"]])
    if not features:
        raise ValueError("no complete windows were created; check sample rate and selected instances")
    return np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.int64)


def metrics(y_true: np.ndarray, y_pred: np.ndarray, labels: list[int]) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(np.mean(precision)), "macro_recall": float(np.mean(recall)),
        "macro_f1": float(np.mean(f1)), "per_class_recall": {str(label): float(value) for label, value in zip(labels, recall)},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "classification_report": classification_report(y_true, y_pred, labels=labels, zero_division=0, output_dict=True),
    }


parser = argparse.ArgumentParser()
parser.add_argument("selection", type=Path, help="output of select_instances.py")
parser.add_argument("--data-root", type=Path, required=True)
parser.add_argument("--artifacts", type=Path, default=Path("ml/artifacts/current"))
parser.add_argument("--split-output", type=Path, default=Path("docs/experiments/3w-split.json"))
parser.add_argument("--seed", type=int, default=20260910)
args = parser.parse_args()

selection = json.loads(args.selection.read_text())
items = selection["instances"]
splits = grouped_split(items, args.seed)
args.split_output.parent.mkdir(parents=True, exist_ok=True)
args.split_output.write_text(json.dumps({"seed": args.seed, "groups": splits}, indent=2) + "\n")
by_group = {str(item.get("well_id") or item["instance_id"]): item for item in items}
train_items = [by_group[group] for group in splits["train"]]
test_items = [by_group[group] for group in splits["test"]]
if not train_items or not test_items:
    raise ValueError("the selected data needs enough groups to create train and test splits")
X_train, y_train = features_for_groups(train_items, args.data_root)
X_test, y_test = features_for_groups(test_items, args.data_root)

normal_train = X_train[y_train == 0]
if len(normal_train) == 0:
    raise ValueError("Isolation Forest requires Normal training windows")
isolation = IsolationForest(random_state=args.seed, contamination="auto").fit(normal_train)
isolation_pred = (isolation.predict(X_test) == -1).astype(int)
isolation_metrics = metrics((y_test != 0).astype(int), isolation_pred, [0, 1])

class_counts = np.bincount(y_train, minlength=len(TARGETS))
class_weight = {index: len(y_train) / (len(TARGETS) * count) for index, count in enumerate(class_counts) if count}
weights = np.asarray([class_weight[label] for label in y_train], dtype=np.float32)
binary = XGBClassifier(
    objective="binary:logistic", n_estimators=200, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, random_state=args.seed, n_jobs=1, eval_metric="logloss",
)
binary.fit(X_train, (y_train != 0).astype(int), sample_weight=weights)
binary_predicted = binary.predict(X_test).astype(int)
binary_metrics = metrics((y_test != 0).astype(int), binary_predicted, [0, 1])
xgb = XGBClassifier(
    objective="multi:softprob", num_class=len(TARGETS), n_estimators=250, max_depth=6,
    learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=args.seed,
    n_jobs=1, eval_metric="mlogloss",
)
xgb.fit(X_train, y_train, sample_weight=weights)
started = perf_counter()
predicted = xgb.predict(X_test).astype(int)
latency_ms = (perf_counter() - started) * 1000 / len(X_test)
xgb_metrics = metrics(y_test, predicted, list(range(len(TARGETS))))
xgb_metrics["cpu_inference_latency_ms_per_window"] = latency_ms

args.artifacts.mkdir(parents=True, exist_ok=True)
joblib.dump(isolation, args.artifacts / "isolation_forest.joblib")
binary.save_model(args.artifacts / "xgboost_binary.json")
xgb.save_model(args.artifacts / "xgboost_model.json")
manifest_sha = hashlib.sha256((args.selection.read_text() + args.split_output.read_text()).encode()).hexdigest()
common_metadata = {
    "training_data_version": "Petrobras 3W Dataset 2.0.0", "features": list(FEATURE_NAMES),
    "window_seconds": 180, "stride_seconds": 10, "created_at": datetime.now(UTC).isoformat(),
    "git_commit": git_commit(), "feature_schema_version": "3w-7v-window-stats-v1",
    "manifest_sha256": manifest_sha,
}
isolation_metadata = {
    **common_metadata, "version": datetime.now(UTC).strftime("if-%Y%m%dT%H%M%SZ"),
    "model_type": "isolation_forest", "class_mapping": {"0": "Normal", "1": "Abnormal"},
    "metrics": isolation_metrics, "artifact_file": "isolation_forest.joblib", "parameters": isolation.get_params(),
}
metadata = {
    **common_metadata, "version": datetime.now(UTC).strftime("xgb-%Y%m%dT%H%M%SZ"), "model_type": "xgboost",
    "class_mapping": {str(index): name for index, name in enumerate(TARGETS.values())},
    "event_code_mapping": {str(index): code for index, code in enumerate(TARGETS)},
    "metrics": xgb_metrics, "artifact_file": "xgboost_model.json", "parameters": xgb.get_params(),
}
(args.artifacts / "isolation_forest_metadata.json").write_text(json.dumps(isolation_metadata, ensure_ascii=False, indent=2, default=str) + "\n")
(args.artifacts / "model_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2, default=str) + "\n")
(args.artifacts / "metrics.json").write_text(json.dumps({"isolation_forest": isolation_metrics, "xgboost_binary": binary_metrics, "xgboost": xgb_metrics}, ensure_ascii=False, indent=2) + "\n")
print(f"Wrote artifacts to {args.artifacts}; test Macro F1={xgb_metrics['macro_f1']:.4f}")
