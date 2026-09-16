from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from statistics import fmean
from uuid import uuid4

from pydantic import AwareDatetime
from fastapi import Depends, FastAPI, HTTPException, WebSocket
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import Base, engine, get_session, migrate_schema
from .inference import InferenceRuntime
from .diagnostics import ControlledDiagnosticService
from .models import Alarm, DiagnosticRecord, EdgeDevice, InferenceResult, Telemetry, Well
from .mqtt import MqttBridge
from .realtime import hub
from .schemas import DeviceStatusIn, DiagnosticRequest, ReplayCommand, TelemetryIn
from .services import acknowledge_alarm, inference_view, persist_inferences, process_device_status, process_telemetry

settings = get_settings()
inference_runtime = InferenceRuntime(settings)
bridge = MqttBridge(settings, inference_runtime)
diagnostic_service = ControlledDiagnosticService(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await migrate_schema(conn)
    inference_runtime.load()
    await bridge.start()
    yield
    await bridge.stop()
    await engine.dispose()


app = FastAPI(title="OilWell AI API", version="0.1.0", lifespan=lifespan)


def alarm_view(row: Alarm) -> dict:
    return {"id": row.id, "well_id": row.well_id, "telemetry_id": row.telemetry_id, "severity": row.severity, "event_type": row.event_type, "status": row.status, "message": row.message, "raised_at": row.raised_at, "acknowledged_at": row.acknowledged_at, "resolved_at": row.resolved_at}


def diagnostic_view(row: DiagnosticRecord) -> dict:
    return {
        "id": row.id, "request_id": row.request_id, "well_id": row.well_id,
        "inference_id": row.inference_id, "status": row.status,
        "model_version": row.model_version, "knowledge_base_version": row.knowledge_base_version,
        "explanation_version": row.explanation_version, "content": row.content,
        "citations": row.citations, "input_summary": row.input_summary,
        "evidence_status": row.evidence_status, "degradation_reasons": row.degradation_reasons,
        "created_at": row.created_at,
    }


async def diagnostic_evidence(session: AsyncSession, inference: InferenceResult) -> tuple[dict, list[dict]]:
    """Reduce persisted telemetry to bounded statistics before any diagnostic call."""
    names = ("P_PDG", "P_TPT", "T_TPT", "P_MON_CKP", "T_JUS_CKP", "P_JUS_CKGL", "QGL")
    rows = (await session.scalars(select(Telemetry).where(
        Telemetry.well_id == inference.well_id, Telemetry.timestamp >= inference.window_start,
        Telemetry.timestamp <= inference.window_end).order_by(Telemetry.timestamp))).all() if inference.window_start and inference.window_end else []
    variables = []
    for name in names:
        values = [float(getattr(row, name.lower())) for row in rows]
        if values:
            variables.append({"name": name, "mean": round(fmean(values), 4), "min": min(values), "max": max(values),
                              "delta": round(values[-1] - values[0], 4), "samples": len(values)})
    alarms = (await session.scalars(select(Alarm).where(Alarm.well_id == inference.well_id)
                                    .order_by(desc(Alarm.raised_at)).limit(5))).all()
    alarm_summary = [{"event_type": row.event_type, "severity": row.severity, "status": row.status,
                      "raised_at": row.raised_at.isoformat() if row.raised_at else None} for row in alarms]
    return {"variables": variables, "sample_count": len(rows), "alarm_context": f"最近报警记录：{len(alarm_summary)} 条。"}, alarm_summary


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok", "mqtt_connected": bridge.client is not None,
        "window_seconds": settings.telemetry_window_seconds,
        "inference_status": inference_runtime.status,
        "inference_error": inference_runtime.load_error,
        "models": inference_runtime.model_status(),
    }


@app.post("/api/telemetry", status_code=202)
async def ingest_telemetry(packet: TelemetryIn, session: AsyncSession = Depends(get_session)) -> dict:
    row = await process_telemetry(session, packet)
    if row is None:
        return {"accepted": False, "reason": "duplicate sequence"}
    event = packet.model_dump(mode="json", by_alias=True)
    hub.add_telemetry(event)
    await hub.broadcast("telemetry", event)
    outcomes = await inference_runtime.add_async(packet.well_id, packet.timestamp, event["measurements"])
    inferences, alarm = await persist_inferences(
        session, row, outcomes, settings.inference_anomaly_threshold,
        settings.inference_confirmation_windows, settings.inference_recovery_windows,
    )
    for inference in inferences:
        await hub.broadcast("inference", inference_view(inference))
    if alarm:
        await hub.broadcast("alarm", alarm_view(alarm))
    return {
        "accepted": True, "telemetry_id": row.id, "inferences": [inference_view(item) for item in inferences],
        "alarm_id": alarm.id if alarm else None,
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
    devices = (await session.scalar(select(func.count()).select_from(EdgeDevice).where(EdgeDevice.status != "OFFLINE", EdgeDevice.last_heartbeat >= datetime.now(timezone.utc) - timedelta(seconds=30)))) or 0
    alarms = (await session.scalar(select(func.count()).select_from(Alarm).where(Alarm.status == "UNACKNOWLEDGED"))) or 0
    return {"wells": wells, "online_devices": devices, "active_alarms": alarms}


@app.get("/api/wells")
async def wells(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.scalars(select(Well).order_by(Well.id))).all()
    return [{"id": well.id, "display_name": well.display_name} for well in rows]


@app.get("/api/wells/{well_id}/telemetry")
async def telemetry_history(well_id: str, limit: int = 360, start: AwareDatetime | None = None, end: AwareDatetime | None = None, session: AsyncSession = Depends(get_session)) -> list[dict]:
    if not 1 <= limit <= 5000:
        raise HTTPException(422, "limit must be between 1 and 5000")
    if start and end and start > end:
        raise HTTPException(422, "start must not be after end")
    statement = select(Telemetry).where(Telemetry.well_id == well_id)
    if start: statement = statement.where(Telemetry.timestamp >= start)
    if end: statement = statement.where(Telemetry.timestamp <= end)
    rows = (await session.scalars(statement.order_by(desc(Telemetry.timestamp), desc(Telemetry.id)).limit(limit))).all()
    return [{"timestamp": item.timestamp, "sequence": item.sequence, "measurements": {"P_PDG": item.p_pdg, "P_TPT": item.p_tpt, "T_TPT": item.t_tpt, "P_MON_CKP": item.p_mon_ckp, "T_JUS_CKP": item.t_jus_ckp, "P_JUS_CKGL": item.p_jus_ckgl, "QGL": item.qgl}, "event_hint": item.event_hint} for item in reversed(rows)]


@app.get("/api/wells/{well_id}/inference")
async def inference_history(well_id: str, mode: str | None = None, limit: int = 360, start: AwareDatetime | None = None, end: AwareDatetime | None = None, event_class: str | None = None, session: AsyncSession = Depends(get_session)) -> list[dict]:
    if not 1 <= limit <= 5000:
        raise HTTPException(422, "limit must be between 1 and 5000")
    if start and end and start > end:
        raise HTTPException(422, "start must not be after end")
    statement = select(InferenceResult).where(InferenceResult.well_id == well_id)
    if start: statement = statement.where(InferenceResult.window_end >= start)
    if end: statement = statement.where(InferenceResult.window_end <= end)
    if event_class:
        if event_class not in {"Normal", "Severe Slugging", "Flow Instability", "Hydrate in Service Line"}:
            raise HTTPException(422, "unsupported event class")
        statement = statement.where(InferenceResult.predicted_class == event_class)
    if mode:
        if mode not in {"active", "shadow"}:
            raise HTTPException(422, "mode must be active or shadow")
        statement = statement.where(InferenceResult.model_mode == mode)
    rows = (await session.scalars(statement.order_by(desc(InferenceResult.id)).limit(limit))).all()
    return [inference_view(item) for item in reversed(rows)]


@app.get("/api/wells/{well_id}/inference/latest")
async def latest_inference(well_id: str, mode: str = "active", session: AsyncSession = Depends(get_session)) -> dict:
    if mode not in {"active", "shadow"}:
        raise HTTPException(422, "mode must be active or shadow")
    result = await session.scalar(
        select(InferenceResult).where(InferenceResult.well_id == well_id, InferenceResult.model_mode == mode)
        .order_by(desc(InferenceResult.id)).limit(1)
    )
    if result is None:
        raise HTTPException(404, "no inference result for well")
    return inference_view(result)


@app.get("/api/models")
async def models() -> list[dict]:
    return inference_runtime.model_status()


@app.get("/api/wells/{well_id}/inference/comparison/latest")
async def latest_comparison(well_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    latest = await session.scalar(select(InferenceResult.telemetry_id).where(InferenceResult.well_id == well_id).order_by(desc(InferenceResult.telemetry_id)).limit(1))
    if latest is None:
        raise HTTPException(404, "no inference result for well")
    rows = (await session.scalars(select(InferenceResult).where(InferenceResult.well_id == well_id, InferenceResult.telemetry_id == latest).order_by(InferenceResult.model_mode))).all()
    return [inference_view(row) for row in rows]


@app.post("/api/wells/{well_id}/diagnostics", status_code=201)
async def create_diagnostic(
    well_id: str, request: DiagnosticRequest, session: AsyncSession = Depends(get_session)
) -> dict:
    """Create an auditable teaching diagnostic from a selected active inference only."""
    inference = await session.get(InferenceResult, request.inference_id)
    if inference is None or inference.well_id != well_id:
        raise HTTPException(404, "inference result not found for well")
    comparison = (await session.scalars(
        select(InferenceResult).where(InferenceResult.well_id == well_id, InferenceResult.telemetry_id == inference.telemetry_id)
    )).all()
    telemetry_summary, alarm_summary = await diagnostic_evidence(session, inference)
    output = await diagnostic_service.diagnose_with_llm(inference, comparison, telemetry_summary, alarm_summary)
    record = DiagnosticRecord(
        well_id=well_id, inference_id=inference.id, request_id=output.request_id,
        status=output.status, model_version=inference.model_version,
        knowledge_base_version=output.knowledge_base_version, explanation_version=output.explanation_version,
        content=output.content, citations=output.citations, input_summary=output.input_summary,
        evidence_status=output.evidence_status, degradation_reasons=output.degradation_reasons,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return diagnostic_view(record)


@app.get("/api/wells/{well_id}/diagnostics")
async def diagnostic_history(well_id: str, limit: int = 20, session: AsyncSession = Depends(get_session)) -> list[dict]:
    if not 1 <= limit <= 100:
        raise HTTPException(422, "limit must be between 1 and 100")
    rows = (await session.scalars(
        select(DiagnosticRecord).where(DiagnosticRecord.well_id == well_id)
        .order_by(desc(DiagnosticRecord.id)).limit(limit)
    )).all()
    return [diagnostic_view(row) for row in rows]


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
    return [{"id": item.id, "status": ("OFFLINE" if item.last_heartbeat is None or (datetime.now(timezone.utc) - item.last_heartbeat.replace(tzinfo=timezone.utc)).total_seconds() > 30 else item.status), "last_heartbeat": item.last_heartbeat, "metrics": item.metadata_} for item in rows]


@app.post("/api/replay/{device_id}/commands", status_code=202)
async def replay_command(device_id: str, command: ReplayCommand) -> dict:
    if command.command == "SET_SPEED" and command.speed is None:
        raise HTTPException(422, "speed is required for SET_SPEED")
    if command.command == "LOAD_INSTANCE" and not command.instance:
        raise HTTPException(422, "instance is required for LOAD_INSTANCE")
    body = {**command.model_dump(exclude_none=True), "command_id": str(uuid4())}
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
