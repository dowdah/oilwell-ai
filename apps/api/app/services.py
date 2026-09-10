from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .inference import InferenceOutcome
from .models import Alarm, AlarmState, EdgeDevice, InferenceResult, Telemetry, Well
from .schemas import DeviceStatusIn, TelemetryIn


async def process_telemetry(session: AsyncSession, packet: TelemetryIn) -> Telemetry | None:
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
        return None
    await session.commit()
    return row


def inference_view(row: InferenceResult) -> dict:
    return {
        "id": row.id, "well_id": row.well_id, "telemetry_id": row.telemetry_id,
        "model_type": row.model_type, "model_mode": row.model_mode,
        "status": row.status, "window_start": row.window_start, "window_end": row.window_end,
        "model_version": row.model_version, "predicted_class": row.predicted_class,
        "confidence": row.confidence, "anomaly_score": row.anomaly_score,
        "feature_schema_version": row.feature_schema_version,
        "inference_latency_ms": row.inference_latency_ms, "created_at": row.created_at,
    }


async def persist_inferences(
    session: AsyncSession,
    telemetry: Telemetry,
    outcomes: list[InferenceOutcome],
    anomaly_threshold: float,
    confirmation_windows: int,
    recovery_windows: int,
) -> tuple[list[InferenceResult], Alarm | None]:
    """Persist active/shadow results separately; only active may change alarm state."""
    results = [InferenceResult(
        well_id=telemetry.well_id, telemetry_id=telemetry.id, status=outcome.status,
        model_type=outcome.model_type, model_mode=outcome.model_mode,
        window_start=outcome.window_start, window_end=outcome.window_end,
        model_version=outcome.model_version, predicted_class=outcome.predicted_class,
        confidence=outcome.confidence, anomaly_score=outcome.anomaly_score,
        feature_schema_version=outcome.feature_schema_version, inference_latency_ms=outcome.latency_ms,
    ) for outcome in outcomes]
    session.add_all(results)
    alarm = None
    active = next((outcome for outcome in outcomes if outcome.model_mode == "active"), None)
    if active and active.status == "predicted":
        state = await session.get(AlarmState, telemetry.well_id)
        if state is None:
            state = AlarmState(well_id=telemetry.well_id, armed=True, abnormal_streak=0, normal_streak=0)
            session.add(state)
        abnormal = active.predicted_class != "Normal" and (active.anomaly_score or 0) >= anomaly_threshold
        if abnormal:
            state.abnormal_streak += 1
            state.normal_streak = 0
            if state.armed and state.abnormal_streak >= confirmation_windows:
                alarm = Alarm(
                    well_id=telemetry.well_id, telemetry_id=telemetry.id, severity="HIGH",
                    event_type=active.predicted_class or "Abnormal",
                    message=(
                        f"Model {active.model_version} confirmed {active.predicted_class}; "
                        f"anomaly score {active.anomaly_score:.3f}. Auxiliary analysis only."
                    ),
                )
                session.add(alarm)
                await session.flush()
                state.armed, state.active_alarm_id = False, alarm.id
        else:
            state.abnormal_streak = 0
            state.normal_streak += 1
            if state.normal_streak >= recovery_windows:
                state.armed, state.active_alarm_id = True, None
    await session.commit()
    for result in results:
        await session.refresh(result)
    return results, alarm


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
