from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .features import CORE_VARIABLES

VARIABLE_ALIASES = {
    "P_PDG": ("P-PDG", "P_PDG"), "P_TPT": ("P-TPT", "P_TPT"),
    "T_TPT": ("T-TPT", "T_TPT"), "P_MON_CKP": ("P-MON-CKP", "P_MON_CKP"),
    "T_JUS_CKP": ("T-JUS-CKP", "T_JUS_CKP"), "P_JUS_CKGL": ("P-JUS-CKGL", "P_JUS_CKGL"),
    "QGL": ("QGL",),
}
LABEL_COLUMNS = ("class", "CLASS", "event", "EVENT", "label", "LABEL")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_parquet(path: Path, root: Path) -> dict[str, Any]:
    """Inspect metadata/batches only; invalid 7-variable instances remain visible."""
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    columns = set(parquet.schema.names)
    mapping = {name: next((raw for raw in aliases if raw in columns), None) for name, aliases in VARIABLE_ALIASES.items()}
    missing = [name for name, raw in mapping.items() if raw is None]
    label_column = next((name for name in LABEL_COLUMNS if name in columns), None)
    nulls = {name: 0 for name in CORE_VARIABLES}
    nonfinite = {name: 0 for name in CORE_VARIABLES}
    stats = {name: {"count": 0, "sum": 0.0, "sum_squared": 0.0, "min": None, "max": None} for name in CORE_VARIABLES}
    rows = 0
    labels: set[str] = set()
    window_counts: dict[str, int] = {}
    run, last_label, previous = 0, None, None
    intervals = Counter()
    time_min, time_max, invalid_times = None, None, 0
    time_column = next((name for name in ("timestamp", "TIMESTAMP", "time", "TIME") if name in columns), None)
    selected = [raw for raw in mapping.values() if raw] + ([label_column] if label_column else []) + ([time_column] if time_column else [])
    for batch in parquet.iter_batches(batch_size=4096, columns=selected):
        for row in batch.to_pylist():
            rows += 1
            valid = not missing
            for name, raw in mapping.items():
                value = row[raw] if raw else None
                if value is None:
                    nulls[name] += 1; valid = False
                elif not math.isfinite(float(value)):
                    nonfinite[name] += 1; valid = False
                else:
                    value = float(value)
                    stat = stats[name]; stat["count"] += 1
                    stat["sum"] += value; stat["sum_squared"] += value * value
                    stat["min"] = value if stat["min"] is None else min(stat["min"], value)
                    stat["max"] = value if stat["max"] is None else max(stat["max"], value)
            timestamp = row[time_column] if time_column else None
            if not isinstance(timestamp, datetime):
                invalid_times += 1; valid = False; timestamp = None
            else:
                time_min = timestamp if time_min is None else min(time_min, timestamp)
                time_max = timestamp if time_max is None else max(time_max, timestamp)
                if previous is not None:
                    delta = (timestamp - previous).total_seconds()
                    intervals[str(delta)] += 1
                    if delta != 1:
                        run = 0
            previous = timestamp
            label = row[label_column] if label_column else None
            if label is not None:
                labels.add(str(label))
            if not valid or label is None:
                run, last_label = 0, None
                continue
            target = str(label)
            if target != last_label:
                run = 0
            last_label = target; run += 1
            if run >= 180 and (run - 180) % 10 == 0:
                window_counts[target] = window_counts.get(target, 0) + 1
    for stat in stats.values():
        count = stat["count"]
        stat["mean"] = stat.pop("sum") / count if count else None
        squared = stat.pop("sum_squared")
        stat["std"] = max(0.0, squared / count - stat["mean"] ** 2) ** 0.5 if count else None
    relative = path.relative_to(root).as_posix()
    filename = path.name.upper()
    domain = "simulated" if filename.startswith("SIMULATED_") else "hand-drawn" if filename.startswith("HAND-DRAWN_") else "real" if filename.startswith("WELL-") else "unknown"
    return {
        "instance_id": relative, "source_path": relative, "sha256": sha256(path), "rows": rows,
        "domain": domain,
        "well_id": (re.match(r"(WELL-\d+)_", path.name).group(1) if re.match(r"(WELL-\d+)_", path.name) else None),
        "time_start": time_min.isoformat() if time_min else None,
        "time_end": time_max.isoformat() if time_max else None,
        "sampling_intervals_seconds": dict(intervals), "invalid_timestamp_rows": invalid_times,
        "nonfinite_counts": nonfinite, "descriptive_statistics": stats,
        "label_values": sorted(labels), "source_columns": mapping,
        "missing_variables": missing,
        "missing_rate": {name: None if raw is None or not rows else nulls[name] / rows for name, raw in mapping.items()},
        "complete_target_window_counts": window_counts,
        "eligible": not missing and label_column is not None and invalid_times == 0 and all(nulls[name] == 0 and nonfinite[name] == 0 for name in CORE_VARIABLES),
        "exclusion_reasons": (["missing_variables"] if missing else []) +
            (["missing_labels"] if label_column is None else []) +
            (["invalid_timestamps"] if invalid_times else []) +
            (["missing_or_nonfinite_values"] if any(nulls.values()) or any(nonfinite.values()) else []),
    }


def build_manifest(root: Path, output: Path) -> dict[str, Any]:
    instances = [inspect_parquet(path, root) for path in sorted(root.rglob("*.parquet"))]
    result = {
        "dataset": "Petrobras 3W Dataset", "version": "2.0.0",
        "generated_at": datetime.now(UTC).isoformat(), "root": "private-local-data-root", "instances": instances,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result
