from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

VARIABLE_ALIASES = {
    "P_PDG": ("P-PDG", "P_PDG"),
    "P_TPT": ("P-TPT", "P_TPT"),
    "T_TPT": ("T-TPT", "T_TPT"),
    "P_MON_CKP": ("P-MON-CKP", "P_MON_CKP"),
    "T_JUS_CKP": ("T-JUS-CKP", "T_JUS_CKP"),
    "P_JUS_CKGL": ("P-JUS-CKGL", "P_JUS_CKGL"),
    "QGL": ("QGL",),
}
TIMESTAMP_COLUMNS = ("timestamp", "TIMESTAMP", "time", "TIME")
EVENT_COLUMNS = ("event", "EVENT", "label", "LABEL", "class", "CLASS")


def _source_column(available: set[str], candidates: tuple[str, ...]) -> str | None:
    return next((column for column in candidates if column in available), None)


def _timestamp(value: object) -> str:
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()
    return str(value) if value is not None else datetime.now(timezone.utc).isoformat()


class ParquetReplay:
    """Streams row batches and never materializes an entire 3W instance."""

    def __init__(self, path: Path, batch_size: int = 256) -> None:
        self.path = path
        self.batch_size = batch_size

    def rows(self) -> Iterator[dict]:
        parquet = pq.ParquetFile(self.path)
        available = set(parquet.schema.names)
        mapping = {target: _source_column(available, aliases) for target, aliases in VARIABLE_ALIASES.items()}
        missing = [target for target, source in mapping.items() if source is None]
        if missing:
            raise ValueError(f"{self.path.name} is missing required variables: {', '.join(missing)}")
        timestamp_column = _source_column(available, TIMESTAMP_COLUMNS)
        event_column = _source_column(available, EVENT_COLUMNS)
        columns = [source for source in mapping.values() if source] + ([timestamp_column] if timestamp_column else []) + ([event_column] if event_column else [])
        for batch in parquet.iter_batches(batch_size=self.batch_size, columns=columns):
            for row in batch.to_pylist():
                yield {
                    "timestamp": _timestamp(row.get(timestamp_column)) if timestamp_column else datetime.now(timezone.utc).isoformat(),
                    "measurements": {target: float(row[source]) for target, source in mapping.items() if row[source] is not None},
                    "event_hint": str(row[event_column]) if event_column and row.get(event_column) is not None else None,
                }
