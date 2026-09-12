import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class Settings:
    device_id: str = os.getenv("EDGE_DEVICE_ID", "edge-pi-01")
    well_id: str = os.getenv("EDGE_WELL_ID", "WELL-00014")
    data_dir: Path = Path(os.getenv("EDGE_DATA_DIR", "/data"))
    replay_file: str | None = os.getenv("EDGE_REPLAY_FILE")
    replay_speed: int = int(os.getenv("EDGE_REPLAY_SPEED", "10"))
    # Demo-only local bootstrap. It deliberately does not publish a command to
    # MQTT, and is off unless a deployment explicitly enables it.
    replay_autostart: bool = _bool("EDGE_REPLAY_AUTOSTART", False)
    mqtt_host: str = os.getenv("MQTT_HOST", "localhost")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "8883"))
    mqtt_username: str | None = os.getenv("MQTT_USERNAME")
    mqtt_password: str | None = os.getenv("MQTT_PASSWORD")
    mqtt_tls: bool = _bool("MQTT_TLS", True)
    mqtt_ca_file: str | None = os.getenv("MQTT_CA_FILE")
    mqtt_topic_prefix: str = os.getenv("MQTT_TOPIC_PREFIX", "3w")
    heartbeat_seconds: int = int(os.getenv("EDGE_HEARTBEAT_SECONDS", "10"))
    batch_size: int = int(os.getenv("EDGE_BATCH_SIZE", "256"))
