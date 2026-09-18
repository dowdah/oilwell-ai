# OilWell AI

边云协同油井智能监测与知识增强辅助分析系统——《石化智能信息系统工程》课程项目。

## Project Overview

系统以 Petrobras 3W 数据回放模拟树莓派边缘设备，完成实时遥测、云端存储、AI 推理、告警历史、实时 Web 可视化，以及受证据约束的 RAG + LLM 辅助诊断。它是教学与人工决策支持系统，不执行自动控制。

## Architecture

`Raspberry Pi Edge → MQTT → FastAPI → PostgreSQL → AI inference → WebSocket → Vue 3 → RAG + LLM Diagnostics`

详见 [系统架构](docs/final/system-architecture.md)。默认分析窗口为 180 秒，固定 7 个变量：`P_PDG`、`P_TPT`、`T_TPT`、`P_MON_CKP`、`T_JUS_CKP`、`P_JUS_CKGL`、`QGL`。

## Core Features

- 3W 真实油井数据回放与树莓派 Edge/Cloud 协同。
- MQTT 遥测、7 变量实时监控、PostgreSQL 历史记录与 Alarm/history。
- XGBoost active 与 TCN shadow 的时序推理边界，以及 WebSocket 驱动的 Vue 3 Dashboard。
- 基于受审阅静态知识清单的轻量关键词检索、受约束引用、可选 OpenAI-compatible LLM 辅助诊断和 `LLM analysis unavailable` 模板降级。
- 诊断只基于窗口统计、实验性模型输出、报警摘要和真实检索资料；不读取完整原始时序，不产生控制命令。

## AI Model Status

- Phase A 曾完成工程推理链路验证；active/shadow、持久化、告警和诊断边界的证据状态见[测试矩阵](docs/final/test-matrix.md)。
- 四分类与二分类的跨井泛化仍受数据覆盖和 domain shift 限制。
- Phase B Binary XGBoost candidate 为 **rejected**，从未部署；详见 [Phase B 报告](docs/phase-b/final-report.md)。
- LLM 输出仅是辅助分析，必须标记为 `Experimental model output`，不是确定故障事实或自动控制结论。

## Repository Structure

| 路径 | 用途 |
| --- | --- |
| `apps/api/` | FastAPI、诊断、推理与 API 测试 |
| `apps/web/` | Vue 3 实时 Dashboard 与 Diagnostics 页面 |
| `services/edge-agent/` | Raspberry Pi 数据回放与 MQTT Edge Agent |
| `infra/` | 本地 Compose、MQTT 与数据库配置 |
| `ml/` | 离线特征、训练、评估和已忽略的模型制品 |
| `docs/knowledge-base/` | 受审阅检索分段及引用元数据 |
| `docs/final/` | 架构、测试矩阵、限制与答辩 Demo 材料 |

## Local Development

不提交真实端点、证书或凭据。复制示例环境配置后按本地 Docker 配置启动：

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

前端开发：

```bash
cd apps/web
npm ci
npm run dev
```

API 文档默认位于 `http://localhost:8000/docs`。LLM 默认关闭；仅在显式配置 OpenAI-compatible API 环境变量后才会调用外部服务。

## Testing

```bash
PYTHONPATH=apps/api python -m pytest apps/api/tests -q
cd apps/web && npm ci && npm run build
```

最新 Phase B/C merge gate：API 33 passed、9 PostgreSQL integration tests skipped（本次未启动临时 PostgreSQL）；前端 production build 通过。最近一次完整 PostgreSQL 环境验证为 9 passed。历史端到端证据与未重复验证项见[测试矩阵](docs/final/test-matrix.md)。

## Limitations

- 当前本地 3W 副本只有 55 个可读实例，旧 187-instance 协议无法复现。
- held-out `WELL-00014` 的 binary XGBoost 结果显示明显 domain shift，验证集高分不能代表跨井泛化。
- LLM 依赖可关闭的外部兼容 API，且只能引用 retriever 实际返回的资料。
- 本系统用于教学与辅助分析，**不构成工业故障诊断或自动控制系统**。

完整边界见 [最终限制说明](docs/final/limitations.md)。

## License

[MIT](LICENSE)
