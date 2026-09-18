#!/usr/bin/env python3
"""Select the pre-registered Phase B candidate using validation evidence only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("reports", nargs="+", type=Path)
parser.add_argument("--output", type=Path, default=Path("ml/artifacts/phase-b/candidate-selection.json"))
args = parser.parse_args()
rows = [json.loads(path.read_text()) for path in args.reports]
keys = {(row["selection_sha256"], row["split_sha256"]) for row in rows}
if len(keys) != 1:
    raise SystemExit("candidate reports must use one frozen selection and split")
if len(rows) > 3:
    raise SystemExit("Phase B permits no more than three candidates")
best = max(rows, key=lambda row: row["validation"]["selected_threshold"]["abnormal"]["f1"])
output = {"selection_rule": "maximum validation abnormal-class F1", "candidate_count": len(rows),
          "selected_candidate": best["candidate"], "threshold": best["validation"]["selected_threshold"]["threshold"],
          "selection_sha256": best["selection_sha256"], "split_sha256": best["split_sha256"],
          "validation": best["validation"]["selected_threshold"],
          "candidates": [{"candidate": row["candidate"], "weighting": row["weighting"],
                          "threshold": row["validation"]["selected_threshold"]["threshold"],
                          "abnormal": row["validation"]["selected_threshold"]["abnormal"]} for row in rows]}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(output, ensure_ascii=False))
