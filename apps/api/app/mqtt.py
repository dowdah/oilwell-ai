import asyncio
import json
import logging
import ssl

import aiomqtt
from pydantic import ValidationError

from .config import Settings
from .database import SessionLocal
from .inference import InferenceRuntime
from .realtime import hub
from .schemas import DeviceStatusIn, TelemetryIn
from .services import inference_view, persist_inference, process_device_status, process_telemetry

logger = logging.getLogger(__name__)


class MqttBridge:
    def __init__(self, settings: Settings, inference_runtime: InferenceRuntime) -> None:
        self.settings = settings
        self.inference_runtime = inference_runtime
        self.client: aiomqtt.Client | None = None
        self.task: asyncio.Task | None = None

    def _tls_context(self) -> ssl.SSLContext | None:
        if not self.settings.mqtt_tls:
            return None
        context = ssl.create_default_context(cafile=str(self.settings.mqtt_ca_file) if self.settings.mqtt_ca_file else None)
        return context

    async def start(self) -> None:
        self.task = asyncio.create_task(self._run(), name="mqtt-bridge")

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def publish_command(self, device_id: str, payload: dict) -> None:
        if not self.client:
            raise RuntimeError("MQTT bridge is not connected")
        await self.client.publish(f"{self.settings.mqtt_topic_prefix}/edge/{device_id}/command", json.dumps(payload))

    async def _run(self) -> None:
        while True:
            try:
                async with aiomqtt.Client(
                    hostname=self.settings.mqtt_host, port=self.settings.mqtt_port,
                    username=self.settings.api_mqtt_username or self.settings.mqtt_username,
                    password=self.settings.api_mqtt_password or self.settings.mqtt_password,
                    tls_context=self._tls_context(),
                ) as client:
                    self.client = client
                    await client.subscribe(f"{self.settings.mqtt_topic_prefix}/edge/+/telemetry")
                    await client.subscribe(f"{self.settings.mqtt_topic_prefix}/edge/+/status")
                    async for message in client.messages:
                        await self._handle(message.topic.value, bytes(message.payload))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.client = None
                logger.warning("MQTT connection lost: %s", exc)
                await asyncio.sleep(5)

    async def _handle(self, topic: str, payload: bytes) -> None:
        try:
            body = json.loads(payload)
            async with SessionLocal() as session:
                if topic.endswith("/telemetry"):
                    packet = TelemetryIn.model_validate(body)
                    row = await process_telemetry(session, packet)
                    if row:
                        event = packet.model_dump(mode="json", by_alias=True)
                        hub.add_telemetry(event)
                        await hub.broadcast("telemetry", event)
                        outcome = self.inference_runtime.add(packet.well_id, packet.timestamp, event["measurements"])
                        inference, alarm = await persist_inference(
                            session, row, outcome, self.settings.inference_anomaly_threshold,
                            self.settings.inference_confirmation_windows, self.settings.inference_recovery_windows,
                        )
                        await hub.broadcast("inference", inference_view(inference))
                        if alarm:
                            await hub.broadcast("alarm", {
                                "id": alarm.id, "well_id": alarm.well_id, "event_type": alarm.event_type,
                                "severity": alarm.severity,
                            })
                elif topic.endswith("/status"):
                    device = await process_device_status(session, DeviceStatusIn.model_validate(body))
                    await hub.broadcast("device_status", {"device_id": device.id, "status": device.status, "last_heartbeat": device.last_heartbeat.isoformat()})
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Discarded invalid MQTT payload on %s: %s", topic, exc)
