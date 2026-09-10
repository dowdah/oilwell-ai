from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Iterable


def _stable_order(values: Iterable[str], seed: int) -> list[str]:
    return sorted(values, key=lambda value: hashlib.sha256(f"{seed}:{value}".encode()).hexdigest())


def grouped_split(records: list[dict], seed: int = 20260910) -> dict[str, list[str]]:
    """Stratify complete groups by label without ever splitting an instance/well."""
    buckets: dict[str, set[str]] = defaultdict(set)
    for record in records:
        label, group = str(record["label"]), str(record.get("well_id") or record["instance_id"])
        buckets[label].add(group)
    splits = {"train": [], "validation": [], "test": []}
    for groups in buckets.values():
        ordered = _stable_order(groups, seed)
        count = len(ordered)
        validation = max(1, round(count * 0.15)) if count >= 3 else 0
        test = max(1, round(count * 0.15)) if count >= 3 else 0
        if validation + test >= count:
            validation, test = (1, 1) if count >= 3 else (0, 1 if count == 2 else 0)
        splits["test"].extend(ordered[:test])
        splits["validation"].extend(ordered[test:test + validation])
        splits["train"].extend(ordered[test + validation:])
    assigned = [group for values in splits.values() for group in values]
    if len(assigned) != len(set(assigned)):
        raise ValueError("a group was assigned to more than one split")
    return {name: sorted(values) for name, values in splits.items()}
