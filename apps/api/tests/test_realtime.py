from datetime import UTC, datetime, timedelta
from app.realtime import RealtimeHub


def test_replay_restart_discards_previous_timeline_and_bounds_the_cache():
    hub = RealtimeHub(window_seconds=180)
    origin = datetime(2026, 1, 1, tzinfo=UTC)
    for cycle in range(3):
        for second in range(220):
            hub.add_telemetry({'well_id': 'test', 'timestamp': (origin + timedelta(seconds=second)).isoformat()})
            assert len(hub.windows['test']) == min(second + 1, 180)
        assert hub.windows['test'][0]['timestamp'] == (origin + timedelta(seconds=40)).isoformat()
    hub.add_telemetry({'well_id': 'test', 'timestamp': (origin + timedelta(seconds=500)).isoformat()})
    assert len(hub.windows['test']) == 1


async def test_inference_timestamps_are_serialized_without_dropping_live_subscriber():
    import json
    class Socket:
        def __init__(self): self.messages = []
        async def accept(self): pass
        async def send_json(self, message): self.messages.append(json.loads(json.dumps(message)))
    socket = Socket()
    hub = RealtimeHub(180)
    await hub.connect(socket)
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    await hub.broadcast('inference', {'well_id': 'test', 'window_start': timestamp, 'window_end': timestamp})
    await hub.broadcast('telemetry', {'well_id': 'test', 'timestamp': timestamp})
    assert socket in hub.clients
    assert len(socket.messages) == 2
    assert socket.messages[0]['payload']['window_start'] == '2026-01-01T00:00:00+00:00'
