#!/usr/bin/env python3
"""Create a deterministic well-disjoint Phase B binary split from an audit."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

SPLITS = ("train", "validation", "test")
TARGETS = {"0": "Normal", "3": "Severe Slugging", "4": "Flow Instability", "9": "Hydrate in Service Line"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def well_sort_key(well: str) -> str:
    return hashlib.sha256(f"20260917:{well}".encode()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--audit", type=Path, default=Path("docs/phase-b/available-data-audit.json"))
parser.add_argument("--selection", type=Path, default=Path("docs/phase-b/frozen/selection.json"))
parser.add_argument("--split-output", type=Path, default=Path("docs/phase-b/frozen/split.json"))
parser.add_argument("--protocol-output", type=Path, default=Path("docs/phase-b/frozen/protocol.json"))
parser.add_argument("--markdown-output", type=Path, default=Path("docs/phase-b/frozen/data-protocol.md"))
args = parser.parse_args()

audit = json.loads(args.audit.read_text())
selection = json.loads(args.selection.read_text())
if selection.get("targets") != TARGETS:
    raise SystemExit("selection does not match the Phase B binary label contract")
rows = audit["instances"]
wells = sorted(audit["per_well"], key=well_sort_key)
if len(wells) < 3:
    raise SystemExit("fewer than three wells are available")
by_well = defaultdict(list)
for row in rows:
    by_well[row["well_id"]].append(row)
total_windows = sum(row["windows"] for row in rows)

def allocation(assignment):
    groups = {name: [] for name in SPLITS}
    for well, index in zip(wells, assignment):
        groups[SPLITS[index]].append(well)
    return groups

def summary(groups):
    result = {}
    for name, group_wells in groups.items():
        group_rows = [row for well in group_wells for row in by_well[well]]
        labels = {row["label"] for row in group_rows}
        normal = sum(row["windows"] for row in group_rows if row["label"] == "0")
        abnormal = sum(row["windows"] for row in group_rows if row["label"] != "0")
        result[name] = {"wells": sorted(group_wells), "labels": sorted(labels), "windows": normal + abnormal,
                        "normal_windows": normal, "abnormal_windows": abnormal,
                        "instance_count": len(group_rows),
                        "raw_label_instances": dict(sorted(Counter(row["label"] for row in group_rows).items()))}
    return result

best = None
for assignment in itertools.product(range(3), repeat=len(wells)):
    if set(assignment) != {0, 1, 2}:
        continue
    groups = allocation(assignment)
    details = summary(groups)
    if any(not details[name]["normal_windows"] or not details[name]["abnormal_windows"] for name in SPLITS):
        continue
    # Training must contain every available raw event class. Prefer a held-out
    # test group with broad raw-event coverage, then the broadest validation.
    if set(details["train"]["labels"]) != set(TARGETS):
        continue
    coverage = (len(details["test"]["labels"]), len(details["validation"]["labels"]))
    balance = sum((details[name]["windows"] / total_windows - target) ** 2
                  for name, target in zip(SPLITS, (.70, .15, .15)))
    # Sorting by the allocation string makes the metadata-only choice stable.
    score = (-coverage[0], -coverage[1], balance, tuple(assignment))
    if best is None or score < best[0]:
        best = (score, groups, details)
if best is None:
    raise SystemExit("no three-way well-disjoint binary split has Normal and Abnormal in every group")
_, groups, details = best
selection_sha = sha256(args.selection)
split = {"seed": 20260917, "groups": {name: details[name]["wells"] for name in SPLITS},
         "method": "exhaustive metadata-only well assignment; binary coverage required in every group"}
args.split_output.parent.mkdir(parents=True, exist_ok=True)
args.split_output.write_text(json.dumps(split, ensure_ascii=False, indent=2) + "\n")
split_sha = sha256(args.split_output)
protocol = {
    "task": "binary_anomaly_detection", "source_dataset_root": audit["source_dataset_root"], "source_instances": audit["available_instances"],
    "normal_label": "0", "abnormal_labels": ["3", "4", "9"], "variables": audit["contract"]["variables"],
    "window_seconds": 180, "step_seconds": 10, "feature_schema": "3w-7v-window-stats-v1", "feature_count": 63,
    "split_unit": "well", "selection_sha256": selection_sha, "split_sha256": split_sha,
    "groups": details, "exclusions": audit["exclusions"], "source_file_hashes": {row["source_path"]: row["sha256"] for row in rows},
    "test_policy": "Candidate and threshold are selected only from training and validation wells; held-out test wells are evaluated once after selection.",
}
args.protocol_output.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n")
lines = ["# Phase B 可读数据协议", "", "## 固定任务", "", "- Normal = `0`; Abnormal = 当前可读 selection 中的 `3` / `4` / `9`。",
         "- 特征：7 variables、180 秒窗口、10 秒步长、63 statistical features。", "- 划分单位：井；不随机切窗口。",
         "- 阈值和候选只使用 validation；test 井仅在最终候选固定后评估一次。", "", "## 数据与可复现性", "",
         f"- source dataset root: `{audit['source_dataset_root']}`", f"- selection SHA-256: `{selection_sha}`", f"- split SHA-256: `{split_sha}`",
         f"- 可用实例：{audit['available_instances']}；排除：{len(audit['exclusions'])}。完整排除清单、文件哈希、连续时长与全零变量见 `../available-data-audit.json`。", "", "## 冻结井级划分", "",
         "| 集合 | 井 | 实例 | Normal 窗口 | Abnormal 窗口 | 原始类实例 |", "| --- | --- | ---: | ---: | ---: | --- |"]
for name in SPLITS:
    group = details[name]
    raw = ", ".join(f"{label}:{count}" for label, count in group["raw_label_instances"].items())
    lines.append(f"| {name} | {', '.join(group['wells'])} | {group['instance_count']} | {group['normal_windows']} | {group['abnormal_windows']} | {raw} |")
lines.extend(["", "## 覆盖边界", "", "- 三个集合均同时具有 Normal 与 Abnormal 窗口，且井集合互斥。",
              "- 原始异常事件类别的跨井覆盖由上表披露；未在 held-out test 出现的类别不得声称具有跨井泛化能力。",
              "- 旧 C2 的 187 实例协议保存在 `../historical/c2-unreproduced-freeze/`，是历史记录，不是本实验输入。"])
args.markdown_output.write_text("\n".join(lines) + "\n")
print(json.dumps({"groups": details, "selection_sha256": selection_sha, "split_sha256": split_sha}, ensure_ascii=False))
