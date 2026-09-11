"""Controlled, auditable RAG-style teaching diagnostics.

The module deliberately has no Telemetry, MQTT, command, or LLM client imports.
It can only work with persisted model-result summaries and reviewed local text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from .config import Settings

DISCLAIMER = "仅教学辅助，不构成操作指令；不得据此执行现场控制或修改报警状态。"
_CONTAINER_KB_PATH = Path("/app/knowledge-base/manifest.json")
_MODULE_PATH = Path(__file__).resolve()
_SOURCE_KB_PATH = (
    _MODULE_PATH.parents[3] / "docs" / "knowledge-base" / "manifest.json"
    if len(_MODULE_PATH.parents) > 3 else _CONTAINER_KB_PATH
)
# Production images package the reviewed manifest beside the application, while
# source-tree tests and local development continue to read the repository copy.
KB_PATH = _CONTAINER_KB_PATH if _CONTAINER_KB_PATH.is_file() else _SOURCE_KB_PATH


class InferenceSummary(Protocol):
    """The narrow result-only boundary accepted by the diagnostic service."""

    id: int
    telemetry_id: int
    model_type: str
    model_mode: str
    status: str
    window_start: datetime | None
    window_end: datetime | None
    model_version: str | None
    predicted_class: str | None
    confidence: float | None
    anomaly_score: float | None
    feature_schema_version: str | None


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    title: str
    url: str
    version: str
    license: str
    tags: tuple[str, ...]
    excerpt: str


class KnowledgeBase:
    def __init__(self, path: Path = KB_PATH) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.version = str(payload["version"])
        self.documents = tuple(KnowledgeDocument(
            id=item["id"], title=item["title"], url=item["url"],
            version=item["version"], license=item["license"],
            tags=tuple(item["tags"]), excerpt=item["excerpt"],
        ) for item in payload["documents"])

    def retrieve(self, query: str, limit: int) -> list[KnowledgeDocument]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        ranked = sorted(
            self.documents,
            key=lambda item: len(terms & set(" ".join((item.title, *item.tags, item.excerpt)).lower().split())),
            reverse=True,
        )
        return [item for item in ranked[:limit] if item.excerpt]


class ExplainabilityCatalog:
    """Reads precomputed SHAP summaries; no raw telemetry is accepted or retained."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def find(self, result: InferenceSummary) -> dict[str, Any] | None:
        path = self.directory / "explanation_manifest.json"
        if not path.is_file() or not result.window_start or not result.window_end:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("model_version") != result.model_version or payload.get("feature_schema_version") != result.feature_schema_version:
            return None
        start, end = result.window_start.isoformat(), result.window_end.isoformat()
        for item in payload.get("window_summaries", []):
            if item.get("window_start") == start and item.get("window_end") == end:
                # Artifacts carry only ranked feature names/contributions and a
                # prose trend summary. Reject anything that looks like raw data.
                if {"top_features", "trend_summary"} <= item.keys() and "measurements" not in item:
                    return {"version": payload.get("version"), **item}
        return None


@dataclass(frozen=True)
class DiagnosticOutput:
    request_id: str
    status: str
    content: str
    citations: list[dict[str, str]]
    input_summary: dict[str, Any]
    knowledge_base_version: str
    explanation_version: str | None
    evidence_status: str
    degradation_reasons: list[str]


class ControlledDiagnosticService:
    def __init__(self, settings: Settings, knowledge_base: KnowledgeBase | None = None) -> None:
        self.settings = settings
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.explanations = ExplainabilityCatalog(settings.explainability_dir)

    def diagnose(self, active: InferenceSummary, comparison: list[InferenceSummary]) -> DiagnosticOutput:
        summary = {
            "inference_id": active.id, "telemetry_id": active.telemetry_id,
            "window_start": active.window_start.isoformat() if active.window_start else None,
            "window_end": active.window_end.isoformat() if active.window_end else None,
            "model_type": active.model_type, "model_mode": active.model_mode,
            "model_version": active.model_version, "predicted_class": active.predicted_class,
            "confidence": active.confidence, "anomaly_score": active.anomaly_score,
            "comparison": [{"model_type": row.model_type, "model_mode": row.model_mode,
                            "predicted_class": row.predicted_class, "confidence": row.confidence}
                           for row in comparison],
        }
        request_id = str(uuid4())
        if active.status != "predicted" or active.model_mode != "active":
            return self._refusal(request_id, summary, "该结果不是可用的 active 预测，无法形成诊断说明。")
        if active.confidence is None or active.confidence < self.settings.diagnostic_min_confidence:
            return self._refusal(request_id, summary, "模型置信度不足，诊断服务拒绝给出事件解释。")
        sources = self.knowledge_base.retrieve(active.predicted_class or "", self.settings.diagnostic_max_sources)
        if not sources:
            return self._refusal(request_id, summary, "知识库没有可引用的公开资料，诊断服务拒答。")
        explanation = self.explanations.find(active)
        source_lines = "；".join(f"[{item.id}] {item.title}" for item in sources)
        evidence = "未找到同窗口的离线 SHAP 摘要，不能推断特征贡献。"
        explanation_version = None
        evidence_status = "degraded"
        degradation_reasons = ["未找到同窗口的离线 SHAP 摘要；未推断特征贡献。"]
        if explanation:
            evidence = f"同窗口离线特征贡献：{', '.join(explanation['top_features'])}。趋势摘要：{explanation['trend_summary']}"
            explanation_version = explanation.get("version")
            evidence_status = "complete"
            degradation_reasons = []
        shadow = next((row for row in comparison if row.model_mode == "shadow"), None)
        contrast = "未提供 shadow 对照结果。" if shadow is None else (
            f"Shadow {shadow.model_type} 结论为 {shadow.predicted_class or shadow.status}"
            f"（置信度 {self._percentage(shadow.confidence)}）。"
        )
        anomaly_score = self._percentage(active.anomaly_score)
        content = (
            f"模型将该窗口分类为“{active.predicted_class}”（置信度 {active.confidence:.1%}，异常分数 {anomaly_score}）。"
            f"{contrast} {evidence} 相关教学资料：{source_lines}。"
            "该说明只描述模型证据与公开资料，未包含完整原始时序、现场参数或控制建议。" + DISCLAIMER
        )
        citations = [{"id": item.id, "title": item.title, "url": item.url, "version": item.version, "license": item.license} for item in sources]
        return DiagnosticOutput(
            request_id, "completed", content, citations, summary,
            self.knowledge_base.version, explanation_version,
            evidence_status, degradation_reasons,
        )

    @staticmethod
    def _percentage(value: float | None) -> str:
        return "未知" if value is None else f"{value:.1%}"

    def _refusal(self, request_id: str, summary: dict[str, Any], reason: str) -> DiagnosticOutput:
        return DiagnosticOutput(
            request_id, "refused", f"{reason}{DISCLAIMER}", [], summary,
            self.knowledge_base.version, None, "refused", [reason],
        )
