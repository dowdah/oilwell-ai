from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
import json

from app.config import Settings
from app.diagnostics import ControlledDiagnosticService


@dataclass
class InferenceResult:
    id: int
    well_id: str
    telemetry_id: int
    model_type: str
    model_mode: str
    status: str
    model_version: str | None
    predicted_class: str | None
    confidence: float | None
    anomaly_score: float | None
    feature_schema_version: str | None
    window_start: datetime | None
    window_end: datetime | None


def result(**overrides) -> InferenceResult:
    defaults = {
        "id": 9, "well_id": "WELL-1", "telemetry_id": 44, "model_type": "xgboost",
        "model_mode": "active", "status": "predicted", "model_version": "xgb-v4",
        "predicted_class": "Flow Instability", "confidence": 0.82, "anomaly_score": 0.79,
        "feature_schema_version": "3w-7v-window-stats-v1",
        "window_start": datetime(2026, 9, 11, tzinfo=UTC),
        "window_end": datetime(2026, 9, 11, tzinfo=UTC) + timedelta(seconds=180),
    }
    defaults.update(overrides)
    return InferenceResult(**defaults)


def test_completed_diagnosis_has_sources_disclaimer_and_no_raw_telemetry(tmp_path) -> None:
    active = result()
    manifest = {
        "version": "explain-v1", "model_version": "xgb-v4",
        "feature_schema_version": "3w-7v-window-stats-v1",
        "window_summaries": [{
            "window_start": active.window_start.isoformat(), "window_end": active.window_end.isoformat(),
            "top_features": ["P_PDG__slope", "QGL__last"], "trend_summary": "离线复核的趋势摘要。",
        }],
    }
    (tmp_path / "explanation_manifest.json").write_text(json.dumps(manifest))
    output = ControlledDiagnosticService(Settings(explainability_dir=tmp_path)).diagnose(active, [active])
    assert output.status == "completed"
    assert output.citations and "仅教学辅助，不构成操作指令" in output.content
    assert "measurements" not in json.dumps(output.input_summary)
    assert output.explanation_version == "explain-v1"


def test_low_confidence_refuses_without_sources_or_explanation(tmp_path) -> None:
    output = ControlledDiagnosticService(Settings(explainability_dir=tmp_path)).diagnose(result(confidence=0.30), [])
    assert output.status == "refused"
    assert output.citations == []
    assert "置信度不足" in output.content


def test_shadow_result_cannot_be_explained_as_active(tmp_path) -> None:
    output = ControlledDiagnosticService(Settings(explainability_dir=tmp_path)).diagnose(result(model_mode="shadow"), [])
    assert output.status == "refused"
    assert "active" in output.content
