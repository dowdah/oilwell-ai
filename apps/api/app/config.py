from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://oilwell:oilwell@localhost:5432/oilwell"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    api_mqtt_username: str | None = None
    api_mqtt_password: str | None = None
    mqtt_tls: bool = False
    mqtt_ca_file: Path | None = None
    mqtt_topic_prefix: str = "3w"
    telemetry_window_seconds: int = 180
    inference_model_dir: Path = Path("/models/current")
    inference_anomaly_threshold: float = 0.50
    inference_confirmation_windows: int = 2
    inference_recovery_windows: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
