"""Controlled, auditable RAG diagnostics with an optional external LLM layer."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import httpx

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
    well_id: str
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
    source_identifier: str
    section: str | None


class KnowledgeBase:
    def __init__(self, path: Path = KB_PATH) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.version = str(payload["version"])
        self.documents = tuple(KnowledgeDocument(
            id=item["id"], title=item["title"], url=item["url"],
            version=item["version"], license=item["license"],
            tags=tuple(item["tags"]), excerpt=item["excerpt"],
            source_identifier=str(item.get("source_identifier", item["id"])), section=item.get("section"),
        ) for item in payload["documents"])

    def retrieve(self, query: str, limit: int) -> list[KnowledgeDocument]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        def score(item):
            return len(terms & set(re.findall(r"[a-z0-9]+", " ".join((item.title, *item.tags, item.excerpt)).lower())))
        ranked = sorted(
            self.documents,
            key=score,
            reverse=True,
        )
        return [item for item in ranked if item.excerpt and score(item) > 0][:limit]


class ExplainabilityCatalog:
    """Reads precomputed SHAP summaries; no raw telemetry is accepted or retained."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def find(self, result: InferenceSummary) -> dict[str, Any] | None:
        path = self.directory / "explanation_manifest.json"
        if not path.is_file() or not result.window_start or not result.window_end:
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if payload.get("model_version") != result.model_version or payload.get("feature_schema_version") != result.feature_schema_version:
            return None
        start, end = result.window_start.isoformat(), result.window_end.isoformat()
        for item in payload.get("window_summaries", []):
            if item.get("well_id") == result.well_id and item.get("window_start") == start and item.get("window_end") == end:
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

    def diagnose(self, active: InferenceSummary, comparison: list[InferenceSummary], telemetry_summary: dict[str, Any] | None = None,
                 alarm_summary: list[dict[str, Any]] | None = None) -> DiagnosticOutput:
        comparison = [row for row in comparison if row.telemetry_id == active.telemetry_id
                      and row.well_id == active.well_id and row.window_start == active.window_start and row.window_end == active.window_end]
        summary = {
            "inference_id": active.id, "telemetry_id": active.telemetry_id, "well_id": active.well_id,
            "window_start": active.window_start.isoformat() if active.window_start else None,
            "window_end": active.window_end.isoformat() if active.window_end else None,
            "model_type": active.model_type, "model_mode": active.model_mode,
            "model_version": active.model_version, "predicted_class": active.predicted_class,
            "confidence": active.confidence, "anomaly_score": active.anomaly_score,
            "comparison": [{"model_type": row.model_type, "model_mode": row.model_mode,
                            "predicted_class": row.predicted_class, "confidence": row.confidence}
                           for row in comparison],
            "telemetry_summary": telemetry_summary or {}, "recent_alarms": alarm_summary or [],
        }
        request_id = str(uuid4())
        if active.status != "predicted" or active.model_mode != "active":
            return self._refusal(request_id, summary, "该结果不是可用的 active 预测，无法形成诊断说明。")
        if active.predicted_class not in {"Normal", "Severe Slugging", "Flow Instability", "Hydrate in Service Line"}:
            return self._refusal(request_id, summary, "模型类别不在已审阅的四类教学范围内，诊断服务拒答。")
        if active.confidence is None or not math.isfinite(active.confidence) or not self.settings.diagnostic_min_confidence <= active.confidence <= 1:
            return self._refusal(request_id, summary, "模型置信度不足，诊断服务拒绝给出事件解释。")
        sources = self.knowledge_base.retrieve(active.predicted_class or "", self.settings.diagnostic_max_sources)
        if not sources:
            return self._refusal(request_id, summary, "Insufficient retrieved evidence：知识库没有可引用的公开资料，诊断服务拒答。")
        explanation = self.explanations.find(active)
        source_lines = "；".join(f"[{item.id}] {item.title}：{item.excerpt}" for item in sources)
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
        content = self._template(summary, active, contrast, evidence, source_lines, "LLM analysis unavailable")
        citations = [{"id": item.id, "title": item.title, "url": item.url, "version": item.version, "license": item.license,
                      "source_identifier": item.source_identifier, "section": item.section} for item in sources]
        return DiagnosticOutput(
            request_id, "completed", content, citations, summary,
            self.knowledge_base.version, explanation_version,
            evidence_status, degradation_reasons,
        )

    async def diagnose_with_llm(self, active: InferenceSummary, comparison: list[InferenceSummary],
                                telemetry_summary: dict[str, Any] | None = None,
                                alarm_summary: list[dict[str, Any]] | None = None) -> DiagnosticOutput:
        """Never let external analysis alter sources, alarms, or model evidence."""
        output = self.diagnose(active, comparison, telemetry_summary, alarm_summary)
        if output.status != "completed":
            return output
        if not (self.settings.diagnostic_llm_enabled and self.settings.diagnostic_llm_base_url
                and self.settings.diagnostic_llm_api_key and self.settings.diagnostic_llm_model):
            return replace(output, evidence_status="degraded", degradation_reasons=output.degradation_reasons + ["LLM analysis unavailable"])
        try:
            text = await self._llm_analysis(output.input_summary, output.citations)
            return replace(output, content=text, evidence_status="complete",
                           degradation_reasons=[item for item in output.degradation_reasons if item != "LLM analysis unavailable"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return replace(output, evidence_status="degraded", degradation_reasons=output.degradation_reasons + ["LLM analysis unavailable"])

    async def _llm_analysis(self, summary: dict[str, Any], citations: list[dict[str, str]]) -> str:
        source_lines = "\n".join(f"[{row['id']}] {row['title']} — {row['version']}" for row in citations)
        prompt = {
            "evidence": summary,
            "retrieved_sources": citations,
            "rules": ["Experimental model output is not a fault fact.", "Do not invent citations or operating instructions.",
                      "Use uncertainty language and only the supplied evidence."],
        }
        messages = [
            {"role": "developer", "content": "Return JSON with monitoring_summary, model_evidence, key_variables, possible_interpretation, recommended_checks, limitations. Chinese prose only; no citations or control commands."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]
        url = self.settings.diagnostic_llm_base_url.rstrip("/") + "/chat/completions"
        async with httpx.AsyncClient(timeout=self.settings.diagnostic_llm_timeout_seconds) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {self.settings.diagnostic_llm_api_key}"},
                                         json={"model": self.settings.diagnostic_llm_model, "messages": messages, "temperature": 0})
            response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        required = ("monitoring_summary", "model_evidence", "key_variables", "possible_interpretation", "recommended_checks", "limitations")
        if not all(isinstance(parsed.get(key), str) and parsed[key].strip() for key in required):
            raise ValueError("LLM response does not satisfy the diagnostic contract")
        references = "\n".join(f"- [{row['id']}] {row['title']} ({row['version']})" for row in citations)
        return (f"## Monitoring Summary\n{parsed['monitoring_summary']}\n\n## Model Evidence\nExperimental model output: {parsed['model_evidence']}\n\n"
                f"## Key Variables\n{parsed['key_variables']}\n\n## Possible Interpretation\n{parsed['possible_interpretation']}\n\n"
                f"## Recommended Checks\n{parsed['recommended_checks']}\n\n## References\n{references}\n\n## Limitations\n{parsed['limitations']}\n{DISCLAIMER}")

    def _template(self, summary: dict[str, Any], active: InferenceSummary, contrast: str, evidence: str,
                  source_lines: str, llm_status: str) -> str:
        telemetry = summary.get("telemetry_summary") or {}
        variables = telemetry.get("variables") or "同窗口七变量统计不可用。"
        alarms = telemetry.get("alarm_context") or "未提供报警历史摘要。"
        return (f"## Monitoring Summary\n井 {active.well_id} 的窗口为 {summary['window_start']} 至 {summary['window_end']}。{alarms}\n\n"
                f"## Model Evidence\nExperimental model output：模型将该窗口分类为“{active.predicted_class}”（置信度 {active.confidence:.1%}，异常分数 {self._percentage(active.anomaly_score)}）。{contrast}\n\n"
                f"## Key Variables\n{evidence} 七变量摘要：{variables}\n\n"
                "## Possible Interpretation\n上述内容仅表示可能的监测线索，需要结合现场工况进一步核实，不能确认故障原因。\n\n"
                "## Recommended Checks\n请由人员核对传感器质量、现场运行记录和既有报警历史；不生成自动控制指令。\n\n"
                f"## References\n{source_lines}\n\n## Limitations\n{llm_status}。仅使用本次检索到的资料；模型输出为实验性结果，不具备已验证的跨井泛化能力。\n{DISCLAIMER}")

    @staticmethod
    def _percentage(value: float | None) -> str:
        return "未知" if value is None else f"{value:.1%}"

    def _refusal(self, request_id: str, summary: dict[str, Any], reason: str) -> DiagnosticOutput:
        return DiagnosticOutput(
            request_id, "refused", f"{reason}{DISCLAIMER}", [], summary,
            self.knowledge_base.version, None, "refused", [reason],
        )
