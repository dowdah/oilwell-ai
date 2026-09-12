"""Streaming 3W windows and train-only normalization for TCN training."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

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


def _mapping(path: Path) -> dict[str, str]:
    import pyarrow.parquet as pq

    columns = set(pq.ParquetFile(path).schema.names)
    mapping = {target: next((name for name in aliases if name in columns), None) for target, aliases in VARIABLE_ALIASES.items()}
    missing = [target for target, source in mapping.items() if source is None]
    if missing:
        raise ValueError(f"{path.name} is missing required variables: {', '.join(missing)}")
    return {target: source for target, source in mapping.items() if source is not None}


def iter_rows(path: Path, target_labels: Sequence[str]) -> Iterator[dict[str, float]]:
    """Read Parquet batches one at a time and never fill missing signals silently."""
    import pyarrow.parquet as pq

    mapping = _mapping(path)
    parquet = pq.ParquetFile(path)
    label_column = next((name for name in LABEL_COLUMNS if name in parquet.schema.names), None)
    if label_column is None:
        raise ValueError(f"{path.name} is missing its observation label column")
    allowed_labels = set(map(str, target_labels))
    for batch in parquet.iter_batches(batch_size=4096, columns=[*mapping.values(), label_column]):
        for row in batch.to_pylist():
            if str(row[label_column]) not in allowed_labels or any(row[source] is None for source in mapping.values()):
                continue
            yield {target: float(row[source]) for target, source in mapping.items()}


def iter_windows(items: Iterable[dict], data_root: Path, window_size: int = 180, stride: int = 10) -> Iterator[tuple[list[dict[str, float]], int]]:
    """Generate windows on demand; only the current 180-row deque stays in memory."""
    for item in items:
        label = int(item["label"])
        observation_labels = item.get("observation_labels", [str(label)])
        allowed_labels = set(map(str, observation_labels))
        buffer: deque[dict[str, float]] = deque(maxlen=window_size)
        complete_rows = 0
        path = data_root / item["source_path"]
        mapping = _mapping(path)
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(path)
        label_column = next((name for name in LABEL_COLUMNS if name in parquet.schema.names), None)
        if label_column is None:
            raise ValueError(f"{path.name} is missing its observation label column")
        for batch in parquet.iter_batches(batch_size=4096, columns=[*mapping.values(), label_column]):
            for row in batch.to_pylist():
                if str(row[label_column]) not in allowed_labels or any(row[source] is None for source in mapping.values()):
                    buffer.clear()
                    complete_rows = 0
                    continue
                buffer.append({target: float(row[source]) for target, source in mapping.items()})
                complete_rows += 1
                if len(buffer) == window_size and (complete_rows - window_size) % stride == 0:
                    yield list(buffer), label


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

    def __init__(self, items: list[dict], data_root: Path, scaler: StandardScaler, window_size: int = 180, stride: int = 10) -> None:
        self.items, self.data_root, self.scaler = items, data_root, scaler
        self.window_size, self.stride = window_size, stride

    def __iter__(self):
        import torch

        for window, label in iter_windows(self.items, self.data_root, self.window_size, self.stride):
            yield torch.tensor(self.scaler.transform(window), dtype=torch.float32), torch.tensor(label, dtype=torch.long)
