"""Shared reporting and provenance for fixed-split offline experiments."""
import hashlib
from pathlib import Path
from time import perf_counter

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support


def report(expected, predicted, labels):
    precision, recall, f1, _ = precision_recall_fscore_support(expected, predicted, labels=labels, zero_division=0)
    present = sorted(set(map(int, expected)))
    return {
        "accuracy": float(accuracy_score(expected, predicted)),
        "macro_precision": float(np.mean(precision)), "macro_recall": float(np.mean(recall)), "macro_f1": float(np.mean(f1)),
        "present_classes": present, "missing_classes": sorted(set(labels) - set(present)),
        "selection_macro_f1_present_classes": float(precision_recall_fscore_support(expected, predicted, labels=present, zero_division=0)[2].mean()),
        "per_class_recall": {str(label): float(value) for label, value in zip(labels, recall)},
        "confusion_matrix": confusion_matrix(expected, predicted, labels=labels).tolist(),
        "classification_report": classification_report(expected, predicted, labels=labels, zero_division=0, output_dict=True),
    }


def latency_samples(predict_one, inputs, limit=30):
    indices = np.linspace(0, len(inputs) - 1, min(limit, len(inputs)), dtype=int)
    predict_one(inputs[indices[0]])
    elapsed = []
    for index in indices:
        started = perf_counter(); predict_one(inputs[index])
        elapsed.append((perf_counter() - started) * 1000)
    return {"samples": len(elapsed), "median_ms": float(np.median(elapsed)),
            "p95_ms": float(np.percentile(elapsed, 95)), "max_ms": max(elapsed),
            "scope": "warm CPU single-window model call; preprocessing excluded"}


def source_hash():
    root = Path(__file__).resolve().parents[2]
    paths = sorted((root / "ml").glob("oilwell_ml/*.py")) + sorted((root / "ml/scripts").glob("*.py"))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode()); digest.update(path.read_bytes())
    return digest.hexdigest()
