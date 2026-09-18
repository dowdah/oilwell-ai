# 系统架构

## System Architecture

```mermaid
flowchart LR
  Edge[Raspberry Pi Edge Agent] -->|MQTT telemetry| Broker[Mosquitto]
  Broker --> API[FastAPI]
  API <--> DB[(PostgreSQL)]
  API --> AI[Active XGBoost / Shadow TCN]
  API --> WS[WebSocket]
  WS --> Web[Vue 3 Dashboard]
  API --> KB[Reviewed Knowledge Base]
  KB --> RAG[Lightweight Retriever]
  AI --> RAG
  RAG --> LLM[Optional OpenAI-compatible LLM]
  LLM --> Diag[Constrained Diagnostic Report]
  Diag --> Web
```

## Telemetry Data Flow

```mermaid
flowchart LR
  Replay[3W replay] --> Edge[Edge Agent]
  Edge --> MQTT[MQTT]
  MQTT --> API[FastAPI]
  API --> PG[(PostgreSQL)]
  API --> Infer[AI inference]
  Infer --> WS[WebSocket]
  WS --> Vue[Vue 3]
  Infer --> Alarm[Alarm / History]
```

## Diagnosis Flow

```mermaid
flowchart LR
  Stats[Window statistics] --> Evidence
  Model[Experimental model result] --> Evidence
  History[Alarm history] --> Evidence
  Chunks[Retrieved reviewed chunks] --> Evidence
  Evidence --> LLM[Optional LLM]
  LLM --> Report[Constrained diagnostic report]
  Chunks --> Cite[Real retriever citations]
  Cite --> Report
  Fallback[LLM unavailable] --> Template[Template report]
```

知识检索目前只对 `docs/knowledge-base/manifest.json` 中的受审阅静态条目做关键词匹配；未实现文档上传、embedding、pgvector 或 FAISS 索引。LLM 不读取完整原始时序、不能生成控制命令，也不能新增引用；外部 API 不可用时保留模板报告，监控链路不受影响。
