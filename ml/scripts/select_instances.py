#!/usr/bin/env python3
"""Create the labelled, shareable instance selection table from an inspector manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGETS = {"0": "Normal", "3": "Severe Slugging", "4": "Flow Instability", "9": "Hydrate in Service Line"}
# Dataset 2.0.0 encodes transient observations as event label + 100.  Event 9
# is therefore represented by both its steady-state label (9) and formally
# labelled transient observations (109); both remain in the same event-9
# source directory and are recorded explicitly in the selection manifest.
OBSERVATION_LABELS = {"0": ("0",), "3": ("3",), "4": ("4",), "9": ("9", "109")}

parser = argparse.ArgumentParser()
parser.add_argument("manifest", type=Path)
parser.add_argument("--output", type=Path, default=Path("docs/experiments/3w-instance-selection.json"))
args = parser.parse_args()
manifest = json.loads(args.manifest.read_text())
selected = []
for instance in manifest["instances"]:
    labels = [str(label) for label in instance.get("label_values", [])]
    source_label = Path(instance["source_path"]).parts[0]
    observation_labels = OBSERVATION_LABELS.get(source_label, ())
    available = sum(int(instance.get("complete_target_window_counts", {}).get(label, 0)) for label in observation_labels)
    if instance["eligible"] and source_label in TARGETS and any(label in labels for label in observation_labels) and available:
        selected.append({
            "instance_id": instance["instance_id"], "source_path": instance["source_path"],
            "label": source_label, "label_name": TARGETS[source_label], "domain": instance["domain"],
            "well_id": None, "sha256": instance["sha256"], "complete_target_windows": available,
            "observation_labels": list(observation_labels),
        })
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({"targets": TARGETS, "observation_labels": OBSERVATION_LABELS, "instances": selected}, ensure_ascii=False, indent=2) + "\n")
counts = {label: sum(item["label"] == label for item in selected) for label in TARGETS}
print(f"Wrote {args.output}; selected counts: {counts}")
