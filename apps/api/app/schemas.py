from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Measurements(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    p_pdg: float = Field(alias="P_PDG")
    p_tpt: float = Field(alias="P_TPT")
    t_tpt: float = Field(alias="T_TPT")
    p_mon_ckp: float = Field(alias="P_MON_CKP")
    t_jus_ckp: float = Field(alias="T_JUS_CKP")
    p_jus_ckgl: float = Field(alias="P_JUS_CKGL")
    qgl: float = Field(alias="QGL")


class TelemetryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=1, max_length=64)
    well_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    sequence: int = Field(ge=0)
    measurements: Measurements
    event_hint: str | None = Field(default=None, max_length=80)
    extras: dict = Field(default_factory=dict)


class DeviceStatusIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    status: Literal["ONLINE", "OFFLINE", "PAUSED", "REPLAYING"]
    metrics: dict = Field(default_factory=dict)


class ReplayCommand(BaseModel):
    command: Literal["START", "STOP", "PAUSE", "SET_SPEED", "LOAD_INSTANCE"]
    speed: Literal[1, 5, 10, 20] | None = None
    instance: str | None = Field(default=None, max_length=256)
