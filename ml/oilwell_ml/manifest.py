from __future__ import annotations

import hashlib
import json
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
    rows = 0
    labels: set[str] = set()
    window_counts: dict[str, int] = {}
    runs: dict[str, int] = {}
    selected = [raw for raw in mapping.values() if raw] + ([label_column] if label_column else [])
    for batch in parquet.iter_batches(batch_size=4096, columns=selected):
        rows += batch.num_rows
        for target, raw in mapping.items():
            if raw:
                nulls[target] += batch.column(batch.schema.get_field_index(raw)).null_count
        if label_column:
            labels.update(str(value) for value in batch.column(batch.schema.get_field_index(label_column)).to_pylist() if value is not None)
        if label_column and not missing:
            for row in batch.to_pylist():
                label = row[label_column]
                valid = label is not None and all(row[raw] is not None for raw in mapping.values() if raw)
                if not valid:
                    runs.clear()
                    continue
                target = str(label)
                for other in list(runs):
                    if other != target:
                        del runs[other]
                runs[target] = runs.get(target, 0) + 1
                if runs[target] >= 180 and (runs[target] - 180) % 10 == 0:
                    window_counts[target] = window_counts.get(target, 0) + 1
    relative = path.relative_to(root).as_posix()
    filename = path.name.upper()
    domain = "simulated" if filename.startswith("SIMULATED_") else "hand-drawn" if filename.startswith("HAND-DRAWN_") else "real" if filename.startswith("WELL-") else "unknown"
    return {
        "instance_id": relative, "source_path": relative, "sha256": sha256(path), "rows": rows,
        "domain": domain, "label_values": sorted(labels), "source_columns": mapping,
        "missing_variables": missing,
        "missing_rate": {name: None if raw is None or not rows else nulls[name] / rows for name, raw in mapping.items()},
        "complete_target_window_counts": window_counts,
        "eligible": not missing and all(nulls[name] == 0 for name in CORE_VARIABLES),
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
