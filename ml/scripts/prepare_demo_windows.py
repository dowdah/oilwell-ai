#!/usr/bin/env python3
"""Create one private, reproducible 180-second feature window per demo class.

The output is deliberately written by the caller to an ignored location. It
contains derived feature values required by ``generate_explanations.py`` but no
raw rows. The public explanation manifest generated from it retains only
ranked feature contributions and an approved trend sentence.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oilwell_ml.features import CORE_VARIABLES, FEATURE_NAMES, window_features
from oilwell_ml.manifest import VARIABLE_ALIASES

TIMESTAMP_COLUMNS = ("timestamp", "TIMESTAMP", "time", "TIME")
TARGETS = ("0", "3", "4", "9")


def timestamp(value: object) -> str:
    if not isinstance(value, datetime):
        raise ValueError("the selected demo instance must contain a datetime timestamp column")
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def first_window(item: dict, data_root: Path, window_size: int) -> dict:
    path = data_root / item["source_path"]
    parquet = pq.ParquetFile(path)
    available = set(parquet.schema.names)
    mapping = {
        target: next((name for name in aliases if name in available), None)
        for target, aliases in VARIABLE_ALIASES.items()
    }
    missing = [target for target, source in mapping.items() if source is None]
    if missing:
        raise ValueError(f"{path.name} is missing required variables: {', '.join(missing)}")
    timestamp_column = next((name for name in TIMESTAMP_COLUMNS if name in available), None)
    if timestamp_column is None:
        raise ValueError(f"{path.name} has no supported timestamp column")

    rows: deque[tuple[str, dict[str, float]]] = deque(maxlen=window_size)
    columns = [*mapping.values(), timestamp_column]
    for batch in parquet.iter_batches(batch_size=4096, columns=columns):
        for row in batch.to_pylist():
            if any(row[source] is None for source in mapping.values()):
                continue
            rows.append((timestamp(row[timestamp_column]), {
                target: float(row[source]) for target, source in mapping.items()
            }))
            if len(rows) == window_size:
                measurements = [values for _, values in rows]
                features = dict(zip(FEATURE_NAMES, window_features(measurements), strict=True))
                return {
                    "label": item["label"], "label_name": item["label_name"],
                    "instance_id": item["instance_id"], "source_sha256": item["sha256"],
                    "window_start": rows[0][0], "window_end": rows[-1][0],
                    "features": features,
                    "trend_summary": (
                        "该脱敏 180 秒窗口由离线流程选取；"
                        "特征贡献仅描述模型证据，需由课程审阅人结合公开资料确认。"
                    ),
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
