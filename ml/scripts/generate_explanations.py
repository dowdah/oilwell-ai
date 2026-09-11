"""Generate reviewable XGBoost contribution summaries without publishing raw windows.

Input JSON is used only on the training workstation and may contain feature values.
The generated manifest stores feature names, signed SHAP contributions and a human
reviewed trend sentence; it intentionally does not store the input values.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from xgboost import DMatrix, XGBClassifier


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--windows-json", type=Path, required=True,
                        help="Private offline input: [{window_start, window_end, features, trend_summary}]")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    metadata = json.loads((args.model_dir / "model_metadata.json").read_text())
    if metadata.get("model_type") != "xgboost":
        raise ValueError("explanations are currently limited to XGBoost artifacts")
    features = metadata["features"]
    windows = json.loads(args.windows_json.read_text())
    if not windows:
        raise ValueError("at least one offline feature window is required")
    matrix = np.array([[float(item["features"][feature]) for feature in features] for item in windows])
    model = XGBClassifier()
    model.load_model(args.model_dir / metadata["artifact_file"])
    probabilities = model.predict_proba(matrix)
    contributions = model.get_booster().predict(DMatrix(matrix, feature_names=features), pred_contribs=True)
    # XGBoost emits either [rows, features + bias] or [rows, classes, features + bias].
    if contributions.ndim == 2:
        contributions = contributions[:, np.newaxis, :]
    selected = np.array([contributions[index, int(np.argmax(probabilities[index])), :-1]
                         for index in range(len(windows))])
    summaries = []
    for index, item in enumerate(windows):
        ranked = np.argsort(np.abs(selected[index]))[::-1][:args.top_k]
        summaries.append({
            "window_start": item["window_start"], "window_end": item["window_end"],
            "top_features": [features[position] for position in ranked],
            "contributions": {features[position]: round(float(selected[index, position]), 6) for position in ranked},
            "trend_summary": item.get("trend_summary", "Offline reviewer did not provide a trend summary."),
        })
    global_ranked = np.argsort(np.mean(np.abs(selected), axis=0))[::-1][:args.top_k]
    output = {
        "version": f"xgb-shap-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "model_version": metadata["version"], "feature_schema_version": metadata["feature_schema_version"],
        "generated_at": datetime.now(timezone.utc).isoformat(), "method": "xgboost pred_contribs (TreeSHAP)",
        "disclaimer": "Feature contributions are model evidence, not causal proof or operational advice.",
        "global_importance": [{"feature": features[position], "mean_abs_contribution": round(float(np.mean(np.abs(selected[:, position]))), 6)} for position in global_ranked],
        "window_summaries": summaries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
