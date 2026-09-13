"""Streaming 3W windows and train-only normalization for TCN training."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import random
from typing import Iterable, Iterator, Sequence

from .windows import labelled_rows, labelled_windows
from .features import CORE_VARIABLES
from .manifest import LABEL_COLUMNS, VARIABLE_ALIASES

try:
    from torch.utils.data import IterableDataset
except ImportError:  # Keep metadata-only tooling importable without torch.
    class IterableDataset:  # type: ignore[no-redef]
        pass


@dataclass(frozen=True)
class StandardScaler:
    mean: tuple[float, ...]
    std: tuple[float, ...]

    def transform(self, rows: list[dict[str, float]]) -> list[list[float]]:
        return [[(float(row[name]) - self.mean[index]) / self.std[index] for row in rows] for index, name in enumerate(CORE_VARIABLES)]

    def to_dict(self) -> dict:
        return {"variables": list(CORE_VARIABLES), "mean": list(self.mean), "std": list(self.std)}

    @classmethod
    def from_dict(cls, value: dict) -> "StandardScaler":
        if value.get("variables") != list(CORE_VARIABLES):
            raise ValueError("scaler variable order does not match the 7-variable contract")
        mean, std = value.get("mean"), value.get("std")
        if not isinstance(mean, list) or not isinstance(std, list) or len(mean) != len(CORE_VARIABLES) or len(std) != len(CORE_VARIABLES):
            raise ValueError("scaler must provide seven mean/std values")
        if any(float(item) <= 0 for item in std):
            raise ValueError("scaler standard deviations must be positive")
        return cls(tuple(float(item) for item in mean), tuple(float(item) for item in std))


def iter_rows(path: Path, target_labels: Sequence[str]) -> Iterator[dict[str, float]]:
    for observation in labelled_rows(path, target_labels):
        if observation is not None:
            yield observation[1]


def iter_windows(items: Iterable[dict], data_root: Path, window_size: int = 180, stride: int = 10) -> Iterator[tuple[list[dict[str, float]], int]]:
    for item in items:
        for window in labelled_windows(data_root / item["source_path"], item.get("observation_labels", [item["label"]]), window_size, stride):
            yield window, int(item["label"])


def fit_scaler(items: Iterable[dict], data_root: Path) -> StandardScaler:
    """Fit scalar statistics from raw training rows only (not val/test windows)."""
    count = 0
    sums = [0.0] * len(CORE_VARIABLES)
    sums_squared = [0.0] * len(CORE_VARIABLES)
    for item in items:
        for row in iter_rows(data_root / item["source_path"], item.get("observation_labels", [item["label"]])):
            count += 1
            for index, name in enumerate(CORE_VARIABLES):
                value = row[name]
                sums[index] += value
                sums_squared[index] += value * value
    if count < 2:
        raise ValueError("at least two complete training rows are required to fit a scaler")
    mean = [value / count for value in sums]
    variance = [max((sums_squared[index] / count) - mean[index] ** 2, 1e-12) for index in range(len(mean))]
    return StandardScaler(tuple(mean), tuple(value ** 0.5 for value in variance))


class StreamingWindowDataset(IterableDataset):
    """A PyTorch-compatible iterable dataset that streams Parquet every epoch."""

    def __init__(self, items: list[dict], data_root: Path, scaler: StandardScaler, window_size: int = 180, stride: int = 10, shuffle_seed: int | None = None) -> None:
        self.items, self.data_root, self.scaler = items, data_root, scaler
        self.window_size, self.stride = window_size, stride
        self.shuffle_seed, self.epoch = shuffle_seed, 0

    def ordered_windows(self):
        if self.shuffle_seed is None:
            yield from iter_windows(self.items, self.data_root, self.window_size, self.stride)
            return
        # Interleave source instances instead of presenting one class for
        # thousands of consecutive steps. Each window appears exactly once.
        rng = random.Random(self.shuffle_seed + self.epoch)
        self.epoch += 1
        streams = [iter(iter_windows([item], self.data_root, self.window_size, self.stride)) for item in self.items]
        while streams:
            index = rng.randrange(len(streams))
            try:
                yield next(streams[index])
            except StopIteration:
                streams.pop(index)

    def __iter__(self):
        import torch

        for window, label in self.ordered_windows():
            yield torch.tensor(self.scaler.transform(window), dtype=torch.float32), torch.tensor(label, dtype=torch.long)
