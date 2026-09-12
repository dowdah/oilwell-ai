from pathlib import Path

import pytest

from edge_agent.replay import ParquetReplay
from edge_agent.config import Settings
import edge_agent.main as edge_main
from edge_agent.main import ReplayController


def test_missing_required_variables_has_actionable_error(tmp_path: Path) -> None:
    pyarrow = pytest.importorskip("pyarrow")
    table = pyarrow.table({"P-PDG": [1.0]})
    path = tmp_path / "incomplete.parquet"
    pyarrow.parquet.write_table(table, path)
    with pytest.raises(ValueError, match="missing required variables"):
        next(ParquetReplay(path).rows())


def test_configured_autostart_is_local_and_runs_once() -> None:
    class Client:
        def publish(self, *_args, **_kwargs):
            return None

    controller = ReplayController(Settings(replay_file="demo.parquet", replay_autostart=True), Client())
    received: list[dict] = []
    controller.command = received.append  # type: ignore[method-assign]
    controller.start_configured_replay_once()
    controller.start_configured_replay_once()
    assert received == [{"command": "START"}]


def test_recreated_controller_uses_a_fresh_integer_sequence_range(monkeypatch) -> None:
    class Client:
        pass

    monkeypatch.setattr(edge_main.time, "time", lambda: 1_789_214_000)
    controller = ReplayController(Settings(), Client())
    assert controller.sequence == 1_789_214_000
