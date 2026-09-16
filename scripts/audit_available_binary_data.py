#!/usr/bin/env python3
"""Audit the currently readable subset of a prior 3W selection without modelling."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from oilwell_ml.features import CORE_VARIABLES
from oilwell_ml.split import group_id
from oilwell_ml.windows import labelled_rows

TARGETS = {"0": "Normal", "3": "Severe Slugging", "4": "Flow Instability", "9": "Hydrate in Service Line"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_selected_signal(path: Path, labels: list[str]) -> dict:
    valid_rows = windows = maximum_run = current_run = 0
    previous = None
    all_zero = {name: True for name in CORE_VARIABLES}
    for observation in labelled_rows(path, labels):
        if observation is None:
            previous = None; current_run = 0
            continue
        timestamp, signals = observation
        if previous is None or (timestamp - previous).total_seconds() != 1:
            current_run = 0
        current_run += 1; previous = timestamp; valid_rows += 1
        maximum_run = max(maximum_run, current_run)
        if current_run >= 180 and (current_run - 180) % 10 == 0:
            windows += 1
        for name, value in signals.items():
            all_zero[name] = all_zero[name] and value == 0.0
    return {"valid_rows": valid_rows, "max_continuous_seconds": maximum_run, "windows": windows,
            "all_zero_variables": [name for name in CORE_VARIABLES if all_zero[name] and valid_rows]}


parser = argparse.ArgumentParser()
parser.add_argument("selection", type=Path, help="historical C2 selection; it is read only")
parser.add_argument("--data-root", type=Path, required=True)
parser.add_argument("--selection-output", type=Path, default=Path("docs/phase-b/frozen/selection.json"))
parser.add_argument("--audit-json", type=Path, default=Path("docs/phase-b/available-data-audit.json"))
parser.add_argument("--audit-markdown", type=Path, default=Path("docs/phase-b/available-data-audit.md"))
args = parser.parse_args()

source = json.loads(args.selection.read_text())
if source.get("targets") != TARGETS:
    raise SystemExit("the source selection must be the fixed 0/3/4/9 C2 mapping")
available, exclusions, rows = [], [], []
for item in source["instances"]:
    path = args.data_root / item["source_path"]
    label = str(item["label"])
    if not path.is_file():
        exclusions.append({"source_path": item["source_path"], "label": label, "reason": "source_file_missing"})
        continue
    signal = inspect_selected_signal(path, list(map(str, item.get("observation_labels", [label]))))
    row = {"source_path": item["source_path"], "label": label, "well_id": group_id(item),
           "sha256": file_sha256(path), **signal}
    rows.append(row)
    if signal["windows"]:
        available.append(item)
    else:
        exclusions.append({"source_path": item["source_path"], "label": label,
                           "reason": "no_complete_180_second_window", **signal})

def label_counts(items, key="label"):
    return {label: sum(str(item[key]) == label for item in items) for label in TARGETS}

available_rows = [row for row in rows if row["windows"]]
by_label_wells = {label: sorted({row["well_id"] for row in available_rows if row["label"] == label}) for label in TARGETS}
per_well = defaultdict(lambda: {"instances": 0, "labels": Counter(), "windows": 0})
for row in available_rows:
    entry = per_well[row["well_id"]]
    entry["instances"] += 1; entry["labels"][row["label"]] += 1; entry["windows"] += row["windows"]
audit = {
    "source_dataset_root": str(args.data_root.resolve()), "source_selection_sha256": file_sha256(args.selection),
    "source_instances": len(source["instances"]), "available_instances": len(available), "exclusions": exclusions,
    "instance_counts_by_label": label_counts(available), "wells_by_label": by_label_wells,
    "unique_wells_by_label": {label: len(wells) for label, wells in by_label_wells.items()},
    "window_counts_by_label": {label: sum(row["windows"] for row in available_rows if row["label"] == label) for label in TARGETS},
    "per_well": {well: {"instances": data["instances"], "labels": dict(sorted(data["labels"].items())), "windows": data["windows"]}
                 for well, data in sorted(per_well.items())},
    "instances": sorted(available_rows, key=lambda row: (row["label"], row["source_path"])),
    "contract": {"variables": list(CORE_VARIABLES), "window_seconds": 180, "step_seconds": 10, "feature_count": 63},
}
args.selection_output.parent.mkdir(parents=True, exist_ok=True)
selection = {"targets": TARGETS, "instances": available, "source": "current-readable-subset-of-historical-c2-selection",
             "source_dataset_root": str(args.data_root.resolve())}
args.selection_output.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n")
args.audit_json.parent.mkdir(parents=True, exist_ok=True)
args.audit_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")

lines = ["# Phase B 当前可读数据审计", "", "仅审计当前可读 3W 文件；没有搜索或补齐缺失文件。", "", "## 覆盖", "",
         f"- 历史 selection 实例：{audit['source_instances']}", f"- 当前可用实例：{audit['available_instances']}",
         f"- 排除实例：{len(exclusions)}（均为缺失源文件或无完整窗口）", "", "| 原始类 | 实例数 | 唯一井数 | 总有效窗口 | 井 |", "| --- | ---: | ---: | ---: | --- |"]
for label in TARGETS:
    lines.append(f"| {label} ({TARGETS[label]}) | {audit['instance_counts_by_label'][label]} | {audit['unique_wells_by_label'][label]} | {audit['window_counts_by_label'][label]} | {', '.join(by_label_wells[label]) or '—'} |")
lines.extend(["", "## 每井覆盖", "", "| 井 | 实例数 | 原始类实例数 | 有效窗口 |", "| --- | ---: | --- | ---: |"])
for well, data in audit["per_well"].items():
    labels = ", ".join(f"{label}:{count}" for label, count in data["labels"].items())
    lines.append(f"| {well} | {data['instances']} | {labels} | {data['windows']} |")
zero_rows = [row for row in available_rows if row["all_zero_variables"]]
lines.extend(["", "## 信号完整性与连续性", "", "- 所有纳入实例均以 7 个变量、有限值、连续 1 Hz、180 秒窗口、10 秒步长重新检查。",
             "- 每实例的有效连续时长、窗口数、文件 SHA-256 与全零变量见 `available-data-audit.json`。",
             f"- 全零变量实例：{len(zero_rows)}；仅披露，不填补、不删除变量、不触发新的 zero-channel 实验。", "", "## 历史基线边界", "",
             "旧 C2 abnormal recall = 0.0051782 是 historical result, not reproduced under the current local dataset copy。它不构成本 Phase B baseline。"])
args.audit_markdown.write_text("\n".join(lines) + "\n")
print(json.dumps({"available_instances": len(available), "exclusions": len(exclusions),
                  "instance_counts_by_label": audit["instance_counts_by_label"], "unique_wells_by_label": audit["unique_wells_by_label"]}))
