from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Well(Base):
    __tablename__ = "wells"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EdgeDevice(Base):
    __tablename__ = "edge_devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), default="OFFLINE")
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = (UniqueConstraint("device_id", "sequence", name="uq_telemetry_device_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("edge_devices.id"), index=True)
    well_id: Mapped[str] = mapped_column(ForeignKey("wells.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    p_pdg: Mapped[float] = mapped_column(Float)
    p_tpt: Mapped[float] = mapped_column(Float)
    t_tpt: Mapped[float] = mapped_column(Float)
    p_mon_ckp: Mapped[float] = mapped_column(Float)
    t_jus_ckp: Mapped[float] = mapped_column(Float)
    p_jus_ckgl: Mapped[float] = mapped_column(Float)
    qgl: Mapped[float] = mapped_column(Float)
    event_hint: Mapped[str | None] = mapped_column(String(80))
    extras: Mapped[dict] = mapped_column(JSONB, default=dict)


class Alarm(Base):
    __tablename__ = "alarms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_id: Mapped[str] = mapped_column(ForeignKey("wells.id"), index=True)
    telemetry_id: Mapped[int | None] = mapped_column(ForeignKey("telemetry.id"))
    severity: Mapped[str] = mapped_column(String(16))
    event_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default="UNACKNOWLEDGED", index=True)
    message: Mapped[str] = mapped_column(Text)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
