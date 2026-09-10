from __future__ import annotations

from statistics import median, stdev
from typing import Mapping, Sequence

CORE_VARIABLES = (
    "P_PDG", "P_TPT", "T_TPT", "P_MON_CKP", "T_JUS_CKP", "P_JUS_CKGL", "QGL",
)
FEATURE_STATS = ("mean", "std", "min", "max", "median", "range", "slope", "last", "first_difference")
FEATURE_NAMES = tuple(f"{variable}__{stat}" for variable in CORE_VARIABLES for stat in FEATURE_STATS)


def window_features(samples: Sequence[Mapping[str, float]]) -> list[float]:
    """Create the 63 deterministic statistical features for one complete window."""
    if not samples:
        raise ValueError("a non-empty window is required")
    output: list[float] = []
    for variable in CORE_VARIABLES:
        series = [float(sample[variable]) for sample in samples]
        slope = 0.0 if len(series) < 2 else (series[-1] - series[0]) / (len(series) - 1)
        first_difference = 0.0 if len(series) < 2 else series[-1] - series[-2]
        output.extend([
            sum(series) / len(series), stdev(series) if len(series) > 1 else 0.0,
            min(series), max(series), median(series), max(series) - min(series),
            slope, series[-1], first_difference,
        ])
    return output
