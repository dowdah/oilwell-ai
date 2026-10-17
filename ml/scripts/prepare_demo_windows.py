#!/usr/bin/env python3
"""Create the first complete replay-aligned 180-row window per demo instance.

The output is deliberately written by the caller to an ignored location. It
contains derived feature values required by ``generate_explanations.py`` but no
raw rows. The public explanation manifest generated from it retains only
ranked feature contributions and an approved trend sentence.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oilwell_ml.features import CORE_VARIABLES, FEATURE_NAMES, window_features
from oilwell_ml.windows import labelled_window_records

TIMESTAMP_COLUMNS = ("timestamp", "TIMESTAMP", "time", "TIME")
TARGETS = ("0", "3", "4", "9")


def timestamp(value: object) -> str:
    if not isinstance(value, datetime):
        raise ValueError("the selected demo instance must contain a datetime timestamp column")
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def first_window(item: dict, data_root: Path, window_size: int) -> dict:
    path = data_root / item["source_path"]
    match = re.match(r"(WELL-\d+)_", path.name)
    source_well = match.group(1) if match else None
    declared_well = item.get("well_id")
    if declared_well is not None and (not isinstance(declared_well, str) or not declared_well.strip()):
        raise ValueError("well_id must be a non-empty string when supplied")
    if source_well and declared_well and source_well != declared_well:
        raise ValueError("well_id conflicts with the replay source filename")
    well_id = source_well or declared_well
    if not well_id:
        raise ValueError("cannot determine well_id from metadata or replay source filename")
    # Serving ignores event labels. Filtering them here can move the first
    # window off the API's 10-second prediction cadence after a label change.
    for rows in labelled_window_records(path, None, window_size):
        measurements = [values for _, values in rows]
        return {
            "label": item["label"], "label_name": item["label_name"],
            "well_id": well_id,
            "instance_id": item["instance_id"], "source_sha256": item["sha256"],
            "window_start": timestamp(rows[0][0]), "window_end": timestamp(rows[-1][0]),
            "features": dict(zip(FEATURE_NAMES, window_features(measurements), strict=True)),
            "trend_summary": "该窗口包含回放起点后的首批 180 个连续 1 Hz 样本；特征贡献仅描述模型证据，不等同于实例类别或现场因果解释。",
        }
    raise ValueError(f"{path.name} contains no complete {window_size}-row window")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--window-size", type=int, default=180)
    args = parser.parse_args()
    if args.window_size != 180:
        raise SystemExit("the deployed inference contract requires a 180-row window")

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    output = args.output.resolve()
    ignored_root = (Path("ml/data/raw").resolve(), Path("docs/.local").resolve())
    if not any(output.is_relative_to(root) for root in ignored_root):
        raise SystemExit("output must be in ignored ml/data/raw or docs/.local")
    windows = []
    for label in TARGETS:
        item = next((row for row in selection["instances"] if row["label"] == label), None)
        if item is None:
            raise SystemExit(f"selection has no eligible instance for label {label}")
        windows.append(first_window(item, args.data_root.resolve(), args.window_size))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(windows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} with {len(windows)} private demo windows")


if __name__ == "__main__":
    main()
