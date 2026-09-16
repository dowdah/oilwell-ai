"""Deterministic, globally disjoint well splits and lossless instance expansion."""
from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Iterable

SPLIT_NAMES = ("train", "validation", "test")


def _stable_order(values: Iterable[str], seed: int) -> list[str]:
    return sorted(values, key=lambda value: hashlib.sha256(f"{seed}:{value}".encode()).hexdigest())


def group_id(record: dict) -> str:
    return str(record.get("well_id") or record.get("source_path") or record["instance_id"])


def expand_split(records: list[dict], splits: dict[str, list[str]]) -> dict[str, list[dict]]:
    """Validate exact group coverage and retain every selected instance."""
    if set(splits) != set(SPLIT_NAMES):
        raise ValueError("split must contain train, validation and test")
    assigned = [group for name in SPLIT_NAMES for group in splits[name]]
    expected = {group_id(record) for record in records}
    if len(assigned) != len(set(assigned)):
        raise ValueError("a group was assigned to more than one split")
    if set(assigned) != expected:
        raise ValueError("split must cover every selected group exactly once")
    if len({record["instance_id"] for record in records}) != len(records):
        raise ValueError("duplicate instance in selection")
    return {name: [record for record in records if group_id(record) in set(splits[name])]
            for name in SPLIT_NAMES}


def grouped_split(records: list[dict], seed: int = 20260910) -> dict[str, list[str]]:
    """Allocate complete wells from metadata only, never model scores."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    groups = _stable_order({group_id(record) for record in records}, seed)
    if len(groups) < 3:
        raise ValueError("at least three independent groups are required")
    labels = sorted({str(record["label"]) for record in records})
    counts = defaultdict(lambda: defaultdict(int))
    for record in records:
        counts[str(record["label"])][group_id(record)] += 1
    n = len(groups)
    size = 3 * n + 3 * len(labels)
    rows, lower, upper = [], [], []

    def constrain(entries, lo, hi):
        row = np.zeros(size)
        for index, value in entries:
            row[index] = value
        rows.append(row); lower.append(lo); upper.append(hi)

    for index in range(n):
        constrain([(3 * index + part, 1) for part in range(3)], 1, 1)
    for part in range(3):
        constrain([(3 * index + part, 1) for index in range(n)], 1, np.inf)
    objective = np.zeros(size)
    for label_index, label in enumerate(labels):
        available = counts[label]
        if len(available) < 2:
            raise ValueError(f"class {label} needs at least two independent groups for train/test")
        for part, fraction in enumerate((0.70, 0.15, 0.15)):
            assignment = [(3 * index + part, available.get(group, 0)) for index, group in enumerate(groups)]
            if part != 1 or len(available) >= 3:
                constrain([(3 * index + part, 1) for index, group in enumerate(groups) if group in available], 1, np.inf)
            deviation = 3 * n + 3 * label_index + part
            target = sum(available.values()) * fraction
            constrain(assignment + [(deviation, -1)], -np.inf, target)
            constrain([(index, -value) for index, value in assignment] + [(deviation, -1)], -np.inf, -target)
            objective[deviation] = 1 / sum(available.values())
    result = milp(objective, integrality=np.r_[np.ones(3 * n), np.zeros(size - 3 * n)],
                  bounds=Bounds(np.zeros(size), np.r_[np.ones(3 * n), np.full(size - 3 * n, np.inf)]),
                  constraints=LinearConstraint(np.asarray(rows), lower, upper), options={"time_limit": 30})
    if not result.success:
        raise ValueError("cannot create disjoint class-covered splits: " + result.message)
    splits = {name: sorted(group for index, group in enumerate(groups) if result.x[3 * index + part] > 0.5)
              for part, name in enumerate(SPLIT_NAMES)}
    expand_split(records, splits)
    return splits
