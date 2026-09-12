import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

from .config import Settings
from .replay import ParquetReplay

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class ReplayController:
    def __init__(self, settings: Settings, client: mqtt.Client) -> None:
        self.settings, self.client = settings, client
        self.lock = threading.Lock()
        self.running, self.paused = False, False
        self.speed = settings.replay_speed if settings.replay_speed in {1, 5, 10, 20} else 10
        self.instance = settings.replay_file
        # PostgreSQL deduplicates telemetry by (device_id, sequence). Starting
        # from a seconds-based epoch keeps the value within a signed INTEGER
        # while making a recreated edge container continue with a fresh range
        # instead of silently losing every replay row to old sequence values.
        self.sequence = int(time.time())
        self.worker: threading.Thread | None = None
        self._autostart_pending = settings.replay_autostart

    @property
    def status_topic(self) -> str:
        return f"{self.settings.mqtt_topic_prefix}/edge/{self.settings.device_id}/status"

    @property
    def telemetry_topic(self) -> str:
        return f"{self.settings.mqtt_topic_prefix}/edge/{self.settings.device_id}/telemetry"

    def publish_status(self) -> None:
        with self.lock:
            status = "PAUSED" if self.paused else ("REPLAYING" if self.running else "ONLINE")
            payload = {"device_id": self.settings.device_id, "timestamp": datetime.now(timezone.utc).isoformat(), "status": status, "metrics": {"speed": self.speed, "instance": self.instance, "sequence": self.sequence}}
        self.client.publish(self.status_topic, json.dumps(payload), qos=1)

    def load_instance(self, instance: str) -> None:
        candidate = (self.settings.data_dir / instance).resolve()
        root = self.settings.data_dir.resolve()
        if root not in candidate.parents or candidate.suffix.lower() != ".parquet":
            raise ValueError("instance must be a .parquet file below EDGE_DATA_DIR")
        if not candidate.is_file():
            raise ValueError("requested instance does not exist")
        self.instance = str(candidate.relative_to(root))

    def command(self, payload: dict) -> None:
        command = payload.get("command")
        with self.lock:
            if command == "SET_SPEED":
                speed = payload.get("speed")
                if speed not in {1, 5, 10, 20}:
                    raise ValueError("speed must be one of 1, 5, 10, 20")
                self.speed = speed
            elif command == "LOAD_INSTANCE":
                self.load_instance(str(payload.get("instance", "")))
            elif command == "PAUSE":
                self.paused = True
            elif command == "STOP":
                self.running, self.paused = False, False
            elif command == "START":
                self.paused = False
                if not self.running:
                    self.running = True
                    self.worker = threading.Thread(target=self._replay, daemon=True)
                    self.worker.start()
            else:
                raise ValueError("unsupported command")
        self.publish_status()

    def start_configured_replay_once(self) -> None:
        """Start one locally configured demo replay without an MQTT command."""
        with self.lock:
            if not self._autostart_pending:
                return
            self._autostart_pending = False
            configured = bool(self.instance)
        if not configured:
            logger.warning("EDGE_REPLAY_AUTOSTART ignored because no replay file is configured")
            return
        self.command({"command": "START"})

    def _replay(self) -> None:
        with self.lock:
            instance = self.instance
        if not instance:
            logger.warning("START ignored because no EDGE_REPLAY_FILE is configured")
            with self.lock:
                self.running = False
            self.publish_status()
            return
        path = (self.settings.data_dir / instance).resolve()
        try:
            for row in ParquetReplay(path, self.settings.batch_size).rows():
                while True:
                    with self.lock:
                        active, paused, speed = self.running, self.paused, self.speed
                    if not active:
                        return
                    if not paused:
                        break
                    time.sleep(0.2)
                with self.lock:
                    self.sequence += 1
                    sequence = self.sequence
                payload = {"device_id": self.settings.device_id, "well_id": self.settings.well_id, "timestamp": row["timestamp"], "sequence": sequence, "measurements": row["measurements"]}
                if row["event_hint"]:
                    payload["event_hint"] = row["event_hint"]
                self.client.publish(self.telemetry_topic, json.dumps(payload), qos=1)
                time.sleep(1 / speed)
        except Exception:
            logger.exception("Replay failed")
        finally:
            with self.lock:
                self.running, self.paused = False, False
            self.publish_status()


def main() -> None:
    settings = Settings()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=settings.device_id)
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    if settings.mqtt_tls:
        client.tls_set(ca_certs=settings.mqtt_ca_file)
    controller = ReplayController(settings, client)

    def on_connect(_: mqtt.Client, __, ___, reason_code, ____):
        logger.info("MQTT connected: %s", reason_code)
        client.subscribe(f"{settings.mqtt_topic_prefix}/edge/{settings.device_id}/command", qos=1)
        controller.publish_status()
        controller.start_configured_replay_once()

    def on_message(_: mqtt.Client, __, message: mqtt.MQTTMessage):
        try:
            controller.command(json.loads(message.payload))
        except (json.JSONDecodeError, ValueError):
            logger.exception("Rejected command")

    client.on_connect, client.on_message = on_connect, on_message
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.loop_start()
    try:
        while True:
            controller.publish_status()
            time.sleep(settings.heartbeat_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
