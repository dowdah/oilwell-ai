from pathlib import Path

import pytest

from edge_agent.replay import ParquetReplay


def test_missing_required_variables_has_actionable_error(tmp_path: Path) -> None:
    pyarrow = pytest.importorskip("pyarrow")
    table = pyarrow.table({"P-PDG": [1.0]})
    path = tmp_path / "incomplete.parquet"
    pyarrow.parquet.write_table(table, path)
    with pytest.raises(ValueError, match="missing required variables"):
        next(ParquetReplay(path).rows())
