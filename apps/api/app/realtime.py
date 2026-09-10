import asyncio
from collections import deque
from datetime import datetime

from fastapi import WebSocket


class RealtimeHub:
    def __init__(self, window_seconds: int) -> None:
        self.clients: set[WebSocket] = set()
        self.windows: dict[str, deque[dict]] = {}
        self.window_seconds = window_seconds

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.clients.discard(websocket)

    def add_telemetry(self, payload: dict) -> None:
        samples = self.windows.setdefault(payload["well_id"], deque())
        samples.append(payload)
        cutoff = datetime.fromisoformat(payload["timestamp"]).timestamp() - self.window_seconds
        while samples and datetime.fromisoformat(samples[0]["timestamp"]).timestamp() < cutoff:
            samples.popleft()

    async def broadcast(self, event: str, payload: dict) -> None:
        message = {"event": event, "payload": payload}
        stale: list[WebSocket] = []
        for client in self.clients:
            try:
                await client.send_json(message)
            except Exception:
                stale.append(client)
        for client in stale:
            self.clients.discard(client)


hub = RealtimeHub(window_seconds=180)
