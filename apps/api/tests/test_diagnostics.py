from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
import json

import pytest

from app.config import Settings
from app.diagnostics import ControlledDiagnosticService, KnowledgeBase


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
    assert output.evidence_status == "complete"
    assert output.degradation_reasons == []


def test_low_confidence_refuses_without_sources_or_explanation(tmp_path) -> None:
    output = ControlledDiagnosticService(Settings(explainability_dir=tmp_path)).diagnose(result(confidence=0.30), [])
    assert output.status == "refused"
    assert output.citations == []
    assert "置信度不足" in output.content
    assert output.evidence_status == "refused"
    assert output.degradation_reasons == ["模型置信度不足，诊断服务拒绝给出事件解释。"]


def test_shadow_result_cannot_be_explained_as_active(tmp_path) -> None:
    output = ControlledDiagnosticService(Settings(explainability_dir=tmp_path)).diagnose(result(model_mode="shadow"), [])
    assert output.status == "refused"
    assert "active" in output.content


def test_missing_explanation_is_audited_safe_degradation(tmp_path) -> None:
    output = ControlledDiagnosticService(Settings(explainability_dir=tmp_path)).diagnose(result(), [])
    assert output.status == "completed"
    assert output.evidence_status == "degraded"
    assert output.explanation_version is None
    assert output.degradation_reasons == ["未找到同窗口的离线 SHAP 摘要；未推断特征贡献。"]
    assert "不能推断特征贡献" in output.content


@pytest.mark.parametrize("event", ["Normal", "Severe Slugging", "Flow Instability", "Hydrate in Service Line"])
def test_each_target_class_has_a_citable_diagnostic(event, tmp_path) -> None:
    output = ControlledDiagnosticService(Settings(explainability_dir=tmp_path)).diagnose(
        result(predicted_class=event), []
    )
    assert output.status == "completed"
    assert output.citations
    assert f"模型将该窗口分类为“{event}”" in output.content


def test_missing_knowledge_entry_refuses_and_records_its_reason(tmp_path) -> None:
    manifest = tmp_path / "empty-knowledge-base.json"
    manifest.write_text(json.dumps({"version": "test-empty", "documents": []}), encoding="utf-8")
    service = ControlledDiagnosticService(
        Settings(explainability_dir=tmp_path), KnowledgeBase(manifest)
    )
    output = service.diagnose(result(), [])
    assert output.status == "refused"
    assert output.evidence_status == "refused"
    assert output.degradation_reasons == ["知识库没有可引用的公开资料，诊断服务拒答。"]
