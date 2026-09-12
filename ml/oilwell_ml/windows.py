"""Shared strict 1 Hz labelled-window reader for both training pipelines."""
from collections import deque
from datetime import datetime
import math
from pathlib import Path

from .manifest import VARIABLE_ALIASES, LABEL_COLUMNS

TIMESTAMP_COLUMNS = ("timestamp", "TIMESTAMP", "time", "TIME")


def labelled_rows(path: Path, target_labels):
    """Yield (timestamp, signals), or None to mark an invalid observation."""
    import pyarrow.parquet as pq
    parquet = pq.ParquetFile(path)
    available = set(parquet.schema.names)
    mapping = {name: next((raw for raw in aliases if raw in available), None)
               for name, aliases in VARIABLE_ALIASES.items()}
    missing = [name for name, raw in mapping.items() if raw is None]
    if missing:
        raise ValueError(f"{path.name} is missing required variables: {', '.join(missing)}")
    label = next((name for name in LABEL_COLUMNS if name in available), None)
    timestamp = next((name for name in TIMESTAMP_COLUMNS if name in available), None)
    if label is None or timestamp is None:
        raise ValueError(f"{path.name} requires observation labels and timestamps")
    allowed = set(map(str, target_labels))
    for batch in parquet.iter_batches(batch_size=4096, columns=[*mapping.values(), label, timestamp]):
        for row in batch.to_pylist():
            if (str(row[label]) not in allowed or not isinstance(row[timestamp], datetime)
                    or any(row[raw] is None or not math.isfinite(float(row[raw])) for raw in mapping.values())):
                yield None
            else:
                yield row[timestamp], {name: float(row[raw]) for name, raw in mapping.items()}


def labelled_window_records(path: Path, target_labels, window_size=180, stride=10):
    if window_size < 1 or stride < 1:
        raise ValueError("window size and stride must be positive")
    buffer = deque(maxlen=window_size)
    previous, count = None, 0
    for observation in labelled_rows(path, target_labels):
        if observation is None:
            buffer.clear(); previous, count = None, 0
            continue
        timestamp, signals = observation
        if previous is not None and (timestamp - previous).total_seconds() != 1:
            buffer.clear(); count = 0
        previous = timestamp
        buffer.append((timestamp, signals)); count += 1
        if len(buffer) == window_size and (count - window_size) % stride == 0:
            yield list(buffer)


def labelled_windows(path: Path, target_labels, window_size=180, stride=10):
    for records in labelled_window_records(path, target_labels, window_size, stride):
        yield [signals for _, signals in records]
