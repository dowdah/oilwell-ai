#!/usr/bin/env python3
"""Train one frozen-split offline Normal/Abnormal XGBoost candidate.

Candidate selection and threshold selection use validation only.  Test evaluation
is opt-in so the caller can keep it to the pre-registered evaluation step.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support, precision_recall_curve, roc_auc_score
from xgboost import XGBClassifier

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oilwell_ml.evaluation import latency_samples, report, source_hash
from oilwell_ml.features import FEATURE_NAMES, window_features
from oilwell_ml.split import expand_split, group_id
from oilwell_ml.weighting import sample_weights
from oilwell_ml.windows import labelled_windows

TARGETS = {"0": "Normal", "3": "Severe Slugging", "4": "Flow Instability", "9": "Hydrate in Service Line"}
ABNORMAL = {"3", "4", "9"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def load_features(items: list[dict], data_root: Path):
    features, binary, original, wells = [], [], [], []
    for item in items:
        label = str(item["label"])
        if label not in TARGETS:
            raise ValueError(f"unsupported label {label}")
        well = group_id(item)
        for window in labelled_windows(data_root / item["source_path"], item.get("observation_labels", [label]), 180, 10):
            features.append(window_features(window))
            binary.append(int(label in ABNORMAL))
            original.append(label)
            wells.append(well)
    if not features:
        raise ValueError("no complete windows were created")
    return (np.asarray(features, dtype=np.float32), np.asarray(binary, dtype=np.int64),
            np.asarray(original), np.asarray(wells))


def scalar(value):
    return value.item() if isinstance(value, np.generic) else value


def binary_metrics(expected, probability, threshold, wells):
    predicted = (probability >= threshold).astype(np.int64)
    summary = report(expected, predicted, [0, 1])
    precision, recall, f1, _ = precision_recall_fscore_support(expected, predicted, labels=[0, 1], zero_division=0)
    matrix = confusion_matrix(expected, predicted, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    summary.update({
        "threshold": float(threshold),
        "abnormal": {"precision": float(precision[1]), "recall": float(recall[1]), "f1": float(f1[1])},
        "false_alarm_rate": float(fp / (fp + tn)) if fp + tn else None,
        "false_positive": fp, "false_negative": fn, "true_positive": tp, "true_negative": tn,
        "pr_auc": float(average_precision_score(expected, probability)) if len(set(expected)) == 2 else None,
        "roc_auc": float(roc_auc_score(expected, probability)) if len(set(expected)) == 2 else None,
    })
    per_well = {}
    for well in sorted(set(wells)):
        mask = wells == well
        per_well[str(well)] = binary_metrics_without_wells(expected[mask], probability[mask], threshold)
    summary["per_well"] = per_well
    return summary


def binary_metrics_without_wells(expected, probability, threshold):
    predicted = (probability >= threshold).astype(np.int64)
    precision, recall, f1, _ = precision_recall_fscore_support(expected, predicted, labels=[0, 1], zero_division=0)
    matrix = confusion_matrix(expected, predicted, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    return {
        "windows": int(len(expected)), "abnormal_windows": int(expected.sum()),
        "normal_windows": int((expected == 0).sum()), "confusion_matrix": matrix.tolist(),
        "abnormal": {"precision": float(precision[1]), "recall": float(recall[1]), "f1": float(f1[1])},
        "false_alarm_rate": float(fp / (fp + tn)) if fp + tn else None,
        "pr_auc": float(average_precision_score(expected, probability)) if len(set(expected)) == 2 else None,
        "roc_auc": float(roc_auc_score(expected, probability)) if len(set(expected)) == 2 else None,
    }


def select_threshold(expected, probability, wells):
    precision, recall, thresholds = precision_recall_curve(expected, probability)
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], np.finfo(float).eps)
    best = int(np.argmax(f1))
    selected = float(thresholds[best])
    curve = [{"threshold": float(threshold), "precision": float(p), "recall": float(r), "f1": float(score)}
             for threshold, p, r, score in zip(thresholds, precision[:-1], recall[:-1], f1)]
    return selected, binary_metrics(expected, probability, selected, wells), curve


def configure(candidate, original_labels, binary_labels, wells):
    params = {"objective": "binary:logistic", "n_estimators": 200, "max_depth": 6, "learning_rate": 0.05,
              "subsample": 0.8, "colsample_bytree": 0.8, "random_state": 20260910, "n_jobs": 1,
              "eval_metric": "logloss"}
    if candidate == "baseline":
        # Exact C2 binary baseline: weights are balanced over source labels 0/3/4/9.
        return params, sample_weights(original_labels), "C2 class weighting over labels 0/3/4/9"
    if candidate == "scale-pos-weight":
        positives = int(binary_labels.sum())
        if not positives or positives == len(binary_labels):
            raise ValueError("scale_pos_weight requires both binary classes")
        params["scale_pos_weight"] = (len(binary_labels) - positives) / positives
        return params, None, "binary scale_pos_weight = normal_windows / abnormal_windows"
    if candidate == "well-balanced":
        return params, sample_weights(original_labels, wells), "C2 label-and-within-label-well weighting"
    raise ValueError(f"unknown candidate {candidate}")


def counts(binary, original, wells):
    return {"windows": int(len(binary)), "binary": {str(key): int(value) for key, value in sorted(Counter(binary).items())},
            "source_labels": {str(key): int(value) for key, value in sorted(Counter(original).items())},
            "wells": {str(key): int(value) for key, value in sorted(Counter(wells).items())}}


parser = argparse.ArgumentParser()
parser.add_argument("--selection", type=Path, default=Path("docs/phase-b/frozen/selection.json"))
parser.add_argument("--split", type=Path, default=Path("docs/phase-b/frozen/split.json"))
parser.add_argument("--protocol", type=Path, default=Path("docs/phase-b/frozen/protocol.json"))
parser.add_argument("--data-root", type=Path, required=True)
parser.add_argument("--candidate", choices=("baseline", "scale-pos-weight", "well-balanced"), required=True)
parser.add_argument("--artifact-dir", type=Path, required=True)
parser.add_argument("--report", type=Path, required=True)
parser.add_argument("--evaluate-test", action="store_true")
args = parser.parse_args()

selection = json.loads(args.selection.read_text())
split = json.loads(args.split.read_text())
protocol = json.loads(args.protocol.read_text())
if selection.get("targets") != TARGETS or protocol["feature_count"] != 63:
    raise SystemExit("Phase B protocol mismatch")
sets = expand_split(selection["instances"], split["groups"])
# Test windows are only materialised during the explicit evaluation run.
loaded = {name: load_features(sets[name], args.data_root) for name in ("train", "validation")}
X_train, y_train, original_train, wells_train = loaded["train"]
X_validation, y_validation, original_validation, wells_validation = loaded["validation"]
params, weights, weighting_note = configure(args.candidate, original_train, y_train, wells_train)
model = XGBClassifier(**params)
started = perf_counter()
model.fit(X_train, y_train, sample_weight=weights)
training_seconds = perf_counter() - started
classes = list(model.classes_)
abnormal_column = classes.index(1)
validation_probability = model.predict_proba(X_validation)[:, abnormal_column]
threshold, validation_selected, curve = select_threshold(y_validation, validation_probability, wells_validation)
validation_default = binary_metrics(y_validation, validation_probability, 0.5, wells_validation)

args.artifact_dir.mkdir(parents=True, exist_ok=True)
artifact = args.artifact_dir / "xgboost_binary.json"
model.save_model(artifact)
artifact_sha256 = file_sha256(artifact)
threshold_payload = {"selection_rule": "maximize validation abnormal-class F1", "selected_threshold": threshold,
                     "validation_default_threshold_0_5": validation_default,
                     "validation_selected_threshold": validation_selected, "curve": curve}
(args.artifact_dir / "threshold.json").write_text(json.dumps(threshold_payload, ensure_ascii=False, indent=2) + "\n")

report_payload = {
    "task": "binary_anomaly_detection", "candidate": args.candidate, "weighting": weighting_note,
    "parameters": {key: scalar(value) for key, value in params.items()}, "selection_sha256": protocol["selection_sha256"],
    "split_sha256": protocol["split_sha256"], "source_commit": git_commit(), "source_sha256": source_hash(),
    "feature_schema": protocol["feature_schema"], "window_seconds": 180, "step_seconds": 10,
    "training_seconds": training_seconds, "artifact_sha256": artifact_sha256,
    "window_counts": {name: counts(*loaded[name][1:]) for name in loaded},
    "validation": {"default_threshold_0_5": validation_default, "selected_threshold": validation_selected},
    "test_evaluated": bool(args.evaluate_test),
}
if args.evaluate_test:
    loaded["test"] = load_features(sets["test"], args.data_root)
    X_test, y_test, original_test, wells_test = loaded["test"]
    probability = model.predict_proba(X_test)[:, abnormal_column]
    report_payload["test"] = {"threshold_0_5": binary_metrics(y_test, probability, 0.5, wells_test),
                              "selected_threshold": binary_metrics(y_test, probability, threshold, wells_test),
                              "latency": latency_samples(lambda row: model.predict_proba(row.reshape(1, -1)), X_test)}
metadata = {
    "task": "binary_anomaly_detection", "model_type": "xgboost_binary", "version": datetime.now(UTC).strftime("phase-b-%Y%m%dT%H%M%SZ"),
    "normal_label": "0", "abnormal_labels": ["3", "4", "9"], "features": list(FEATURE_NAMES),
    "feature_schema": protocol["feature_schema"], "window_seconds": 180, "step_seconds": 10, "threshold": threshold,
    "training_split_sha256": protocol["split_sha256"], "selection_sha256": protocol["selection_sha256"],
    "source_commit": git_commit(), "source_sha256": source_hash(), "artifact_file": artifact.name,
    "artifact_sha256": artifact_sha256, "parameters": report_payload["parameters"], "candidate": args.candidate,
}
(args.artifact_dir / "model_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
(args.artifact_dir / "metrics.json").write_text(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n")
args.report.parent.mkdir(parents=True, exist_ok=True)
args.report.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n")
protocol["window_counts"] = {name: counts(*loaded[name][1:]) for name in loaded}
args.protocol.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"candidate": args.candidate, "threshold": threshold,
                  "validation_abnormal": validation_selected["abnormal"],
                  "test_evaluated": args.evaluate_test, "artifact_sha256": artifact_sha256}, ensure_ascii=False))
