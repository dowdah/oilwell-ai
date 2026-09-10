from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Alarm, EdgeDevice, Telemetry, Well
from .schemas import DeviceStatusIn, TelemetryIn


async def process_telemetry(session: AsyncSession, packet: TelemetryIn) -> tuple[Telemetry | None, Alarm | None]:
    if await session.get(Well, packet.well_id) is None:
        session.add(Well(id=packet.well_id, display_name=packet.well_id))
    device = await session.get(EdgeDevice, packet.device_id)
    if device is None:
        device = EdgeDevice(id=packet.device_id, status="REPLAYING", last_heartbeat=packet.timestamp)
        session.add(device)
    else:
        device.status, device.last_heartbeat = "REPLAYING", packet.timestamp

    values = packet.measurements
    row = Telemetry(
        device_id=packet.device_id, well_id=packet.well_id, timestamp=packet.timestamp, sequence=packet.sequence,
        p_pdg=values.p_pdg, p_tpt=values.p_tpt, t_tpt=values.t_tpt, p_mon_ckp=values.p_mon_ckp,
        t_jus_ckp=values.t_jus_ckp, p_jus_ckgl=values.p_jus_ckgl, qgl=values.qgl,
        event_hint=packet.event_hint, extras=packet.extras,
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return None, None

    alarm = None
    if packet.event_hint and packet.event_hint.lower() not in {"normal", "0"}:
        alarm = Alarm(
            well_id=packet.well_id, telemetry_id=row.id,
            severity="HIGH", event_type=packet.event_hint,
            message=f"Replay event hint: {packet.event_hint}",
        )
        session.add(alarm)
    await session.commit()
    return row, alarm


async def process_device_status(session: AsyncSession, status: DeviceStatusIn) -> EdgeDevice:
    device = await session.get(EdgeDevice, status.device_id)
    if device is None:
        device = EdgeDevice(id=status.device_id)
        session.add(device)
    device.status = status.status
    device.last_heartbeat = status.timestamp
    device.metadata_ = status.metrics
    await session.commit()
    return device


async def acknowledge_alarm(session: AsyncSession, alarm_id: int) -> Alarm | None:
    alarm = await session.get(Alarm, alarm_id)
    if alarm is None:
        return None
    alarm.status = "ACKNOWLEDGED"
    alarm.acknowledged_at = datetime.now(timezone.utc)
    await session.commit()
    return alarm
