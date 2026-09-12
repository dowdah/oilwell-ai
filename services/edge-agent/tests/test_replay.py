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

    monkeypatch.setattr(edge_main.time, "time_ns", lambda: 1_789_214_000_000_000_000)
    controller = ReplayController(Settings(), Client())
    assert controller.sequence == 1_789_214_000_000_000


def test_commands_report_applied_state_and_cannot_replace_a_running_instance(tmp_path):
    import json
    class Client:
        def __init__(self): self.messages = []
        def publish(self, topic, payload, **kwargs): self.messages.append(json.loads(payload))
    client = Client()
    (tmp_path / 'demo.parquet').touch()
    controller = ReplayController(Settings(data_dir=tmp_path), client)
    controller.command({'command': 'LOAD_INSTANCE', 'instance': 'demo.parquet', 'command_id': 'load-1'})
    assert client.messages[-1]['metrics']['last_command']['command_id'] == 'load-1'
    assert client.messages[-1]['metrics']['available_instances'] == ['demo.parquet']
    controller.running = True
    with pytest.raises(ValueError, match='stop replay'):
        controller.command({'command': 'LOAD_INSTANCE', 'instance': 'demo.parquet'})
    controller.command({'command': 'PAUSE', 'command_id': 'pause-1'})
    assert client.messages[-1]['status'] == 'PAUSED'
    controller.command({'command': 'SET_SPEED', 'speed': 20})
    assert controller.speed == 20
    controller.command({'command': 'STOP'})
    assert not controller.running and not controller.paused
    assert client.messages[-1]['status'] == 'ONLINE'


def test_old_worker_cannot_stop_a_new_generation(tmp_path, monkeypatch):
    class Client:
        def publish(self, *args, **kwargs): pass
    controller = ReplayController(Settings(data_dir=tmp_path, replay_file='demo.parquet'), Client())
    controller.running = True
    controller.generation = 2
    monkeypatch.setattr(edge_main.ParquetReplay, 'rows', lambda self: iter([]))
    controller._replay(1)
    assert controller.running


def test_sequence_lease_survives_restart_and_backwards_clock(tmp_path, monkeypatch):
    import edge_agent.sequence as sequence
    monkeypatch.setattr(sequence.time, 'time_ns', lambda: 1_000_000_000)
    path = tmp_path / 'sequence.json'
    first = sequence.SequenceAllocator(path, lease_size=5)
    emitted = [first.next() for _ in range(12)]
    monkeypatch.setattr(sequence.time, 'time_ns', lambda: 0)
    second = sequence.SequenceAllocator(path, lease_size=5)
    assert second.next() > max(emitted)
    third = sequence.SequenceAllocator(path, lease_size=5)
    assert third.next() > second.value


def test_invalid_durable_sequence_state_is_not_silently_reset(tmp_path):
    from edge_agent.sequence import SequenceAllocator
    path = tmp_path / 'sequence.json'
    path.write_text('{"reserved_until": 12}')
    with pytest.raises(ValueError, match='invalid sequence state'):
        SequenceAllocator(path)


@pytest.mark.parametrize('invalid', ['missing_time', 'null_time', 'nan', 'null'])
def test_replay_never_fabricates_timestamps_or_partial_measurements(tmp_path, invalid):
    from datetime import datetime
    import pyarrow as pa
    import pyarrow.parquet as pq
    from edge_agent.replay import VARIABLE_ALIASES
    row = {name: [1.0] for name in VARIABLE_ALIASES}
    if invalid != 'missing_time':
        row['timestamp'] = pa.array([None if invalid == 'null_time' else datetime(2026, 1, 1)], type=pa.timestamp('us'))
    if invalid in {'nan', 'null'}:
        row['QGL'] = [float('nan') if invalid == 'nan' else None]
    path = tmp_path / 'invalid.parquet'
    pq.write_table(pa.table(row), path)
    with pytest.raises(ValueError, match='timestamp|measurements'):
        list(ParquetReplay(path).rows())
