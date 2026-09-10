#!/usr/bin/env python3
"""Produce a compact, data-free EDA summary and one representative trend figure."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pyarrow.parquet as pq

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oilwell_ml.manifest import VARIABLE_ALIASES

parser = argparse.ArgumentParser()
parser.add_argument("manifest", type=Path)
parser.add_argument("selection", type=Path)
parser.add_argument("--data-root", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, default=Path("docs/experiments"))
args = parser.parse_args()

manifest = json.loads(args.manifest.read_text())
selection = json.loads(args.selection.read_text())["instances"]
instances = manifest["instances"]
summary = {
    "instance_count": len(instances),
    "eligible_instance_count": sum(item["eligible"] for item in instances),
    "domain_counts": dict(Counter(item["domain"] for item in instances)),
    "label_counts": dict(Counter(label for item in instances for label in item["label_values"])),
    "selected_label_counts": dict(Counter(item["label"] for item in selection)),
    "mean_missing_rate": {
        name: sum(item["missing_rate"][name] or 0 for item in instances) / max(1, len(instances))
        for name in VARIABLE_ALIASES
    },
}
args.output_dir.mkdir(parents=True, exist_ok=True)
(args.output_dir / "3w-eda-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
if not selection:
    raise SystemExit("No selected eligible instances; EDA summary was written but no trend plot was created.")

item = selection[0]
path = args.data_root / item["source_path"]
parquet = pq.ParquetFile(path)
columns = set(parquet.schema.names)
mapping = {name: next(raw for raw in aliases if raw in columns) for name, aliases in VARIABLE_ALIASES.items()}
batch = next(parquet.iter_batches(batch_size=600, columns=list(mapping.values())))
data = batch.to_pydict()
figure, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=True)
for axis, (name, raw) in zip(axes, list(mapping.items())[:4]):
    axis.plot(data[raw], linewidth=0.8)
    axis.set_ylabel(name)
axes[-1].set_xlabel("sample index")
figure.suptitle(f"Representative 3W trend: {item['instance_id']} ({item['label_name']})")
figure.tight_layout()
figure.savefig(args.output_dir / "3w-representative-trend.png", dpi=160)
print(f"Wrote EDA summary and representative trend to {args.output_dir}")
