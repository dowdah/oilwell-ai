#!/usr/bin/env python3
"""Create the labelled, shareable instance selection table from an inspector manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGETS = {"0": "Normal", "3": "Severe Slugging", "4": "Flow Instability", "9": "Hydrate in Service Line"}

parser = argparse.ArgumentParser()
parser.add_argument("manifest", type=Path)
parser.add_argument("--output", type=Path, default=Path("docs/experiments/3w-instance-selection.json"))
args = parser.parse_args()
manifest = json.loads(args.manifest.read_text())
selected = []
for instance in manifest["instances"]:
    labels = [str(label) for label in instance.get("label_values", [])]
    if instance["eligible"] and len(labels) == 1 and labels[0] in TARGETS:
        selected.append({
            "instance_id": instance["instance_id"], "source_path": instance["source_path"],
            "label": labels[0], "label_name": TARGETS[labels[0]], "domain": instance["domain"],
            "well_id": None, "sha256": instance["sha256"],
        })
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({"targets": TARGETS, "instances": selected}, ensure_ascii=False, indent=2) + "\n")
counts = {label: sum(item["label"] == label for item in selected) for label in TARGETS}
print(f"Wrote {args.output}; selected counts: {counts}")
