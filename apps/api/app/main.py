from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, WebSocket
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import Base, engine, get_session
from .inference import InferenceRuntime
from .models import Alarm, EdgeDevice, InferenceResult, Telemetry, Well
from .mqtt import MqttBridge
from .realtime import hub
from .schemas import DeviceStatusIn, ReplayCommand, TelemetryIn
from .services import acknowledge_alarm, inference_view, persist_inference, process_device_status, process_telemetry

settings = get_settings()
inference_runtime = InferenceRuntime(settings)
bridge = MqttBridge(settings, inference_runtime)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    inference_runtime.load()
    await bridge.start()
    yield
    await bridge.stop()
    await engine.dispose()


app = FastAPI(title="OilWell AI API", version="0.1.0", lifespan=lifespan)


def alarm_view(row: Alarm) -> dict:
    return {"id": row.id, "well_id": row.well_id, "telemetry_id": row.telemetry_id, "severity": row.severity, "event_type": row.event_type, "status": row.status, "message": row.message, "raised_at": row.raised_at, "acknowledged_at": row.acknowledged_at}


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok", "mqtt_connected": bridge.client is not None,
        "window_seconds": settings.telemetry_window_seconds,
        "inference_status": inference_runtime.status,
        "inference_error": inference_runtime.load_error,
    }


@app.post("/api/telemetry", status_code=202)
async def ingest_telemetry(packet: TelemetryIn, session: AsyncSession = Depends(get_session)) -> dict:
    row = await process_telemetry(session, packet)
    if row is None:
        return {"accepted": False, "reason": "duplicate sequence"}
    event = packet.model_dump(mode="json", by_alias=True)
    hub.add_telemetry(event)
    await hub.broadcast("telemetry", event)
    outcome = inference_runtime.add(packet.well_id, packet.timestamp, event["measurements"])
    inference, alarm = await persist_inference(
        session, row, outcome, settings.inference_anomaly_threshold,
        settings.inference_confirmation_windows, settings.inference_recovery_windows,
    )
    await hub.broadcast("inference", inference_view(inference))
    if alarm:
        await hub.broadcast("alarm", alarm_view(alarm))
    return {
        "accepted": True, "telemetry_id": row.id, "inference_id": inference.id,
        "inference_status": inference.status, "alarm_id": alarm.id if alarm else None,
    }


@app.post("/api/edge-devices/status", status_code=202)
async def ingest_status(status: DeviceStatusIn, session: AsyncSession = Depends(get_session)) -> dict:
    device = await process_device_status(session, status)
    result = {"device_id": device.id, "status": device.status, "last_heartbeat": device.last_heartbeat.isoformat()}
    await hub.broadcast("device_status", result)
    return result


@app.get("/api/dashboard")
async def dashboard(session: AsyncSession = Depends(get_session)) -> dict:
    wells = (await session.scalar(select(func.count()).select_from(Well))) or 0
    devices = (await session.scalar(select(func.count()).select_from(EdgeDevice).where(EdgeDevice.status != "OFFLINE"))) or 0
    alarms = (await session.scalar(select(func.count()).select_from(Alarm).where(Alarm.status == "UNACKNOWLEDGED"))) or 0
    return {"wells": wells, "online_devices": devices, "active_alarms": alarms}


@app.get("/api/wells")
async def wells(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.scalars(select(Well).order_by(Well.id))).all()
    return [{"id": well.id, "display_name": well.display_name} for well in rows]


@app.get("/api/wells/{well_id}/telemetry")
async def telemetry_history(well_id: str, limit: int = 360, session: AsyncSession = Depends(get_session)) -> list[dict]:
    if not 1 <= limit <= 5000:
        raise HTTPException(422, "limit must be between 1 and 5000")
    rows = (await session.scalars(select(Telemetry).where(Telemetry.well_id == well_id).order_by(desc(Telemetry.timestamp)).limit(limit))).all()
    return [{"timestamp": item.timestamp, "sequence": item.sequence, "measurements": {"P_PDG": item.p_pdg, "P_TPT": item.p_tpt, "T_TPT": item.t_tpt, "P_MON_CKP": item.p_mon_ckp, "T_JUS_CKP": item.t_jus_ckp, "P_JUS_CKGL": item.p_jus_ckgl, "QGL": item.qgl}, "event_hint": item.event_hint} for item in reversed(rows)]


@app.get("/api/wells/{well_id}/inference")
async def inference_history(well_id: str, limit: int = 360, session: AsyncSession = Depends(get_session)) -> list[dict]:
    if not 1 <= limit <= 5000:
        raise HTTPException(422, "limit must be between 1 and 5000")
    rows = (await session.scalars(
        select(InferenceResult).where(InferenceResult.well_id == well_id)
        .order_by(desc(InferenceResult.id)).limit(limit)
    )).all()
    return [inference_view(item) for item in reversed(rows)]


@app.get("/api/wells/{well_id}/inference/latest")
async def latest_inference(well_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.scalar(
        select(InferenceResult).where(InferenceResult.well_id == well_id)
        .order_by(desc(InferenceResult.id)).limit(1)
    )
    if result is None:
        raise HTTPException(404, "no inference result for well")
    return inference_view(result)


@app.get("/api/alarms")
async def alarms(status: str | None = None, session: AsyncSession = Depends(get_session)) -> list[dict]:
    statement = select(Alarm).order_by(desc(Alarm.raised_at)).limit(200)
    if status:
        statement = statement.where(Alarm.status == status)
    return [alarm_view(item) for item in (await session.scalars(statement)).all()]


@app.post("/api/alarms/{alarm_id}/acknowledge")
async def acknowledge(alarm_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    alarm = await acknowledge_alarm(session, alarm_id)
    if not alarm:
        raise HTTPException(404, "alarm not found")
    result = alarm_view(alarm)
    await hub.broadcast("alarm_updated", result)
    return result


@app.get("/api/edge-devices")
async def edge_devices(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.scalars(select(EdgeDevice).order_by(EdgeDevice.id))).all()
    return [{"id": item.id, "status": item.status, "last_heartbeat": item.last_heartbeat, "metrics": item.metadata_} for item in rows]


@app.post("/api/replay/{device_id}/commands", status_code=202)
async def replay_command(device_id: str, command: ReplayCommand) -> dict:
    if command.command == "SET_SPEED" and command.speed is None:
        raise HTTPException(422, "speed is required for SET_SPEED")
    if command.command == "LOAD_INSTANCE" and not command.instance:
        raise HTTPException(422, "instance is required for LOAD_INSTANCE")
    body = command.model_dump(exclude_none=True)
    try:
        await bridge.publish_command(device_id, body)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"queued": True, "device_id": device_id, **body}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        hub.disconnect(websocket)
