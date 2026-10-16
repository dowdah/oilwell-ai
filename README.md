# OilWell AI

边云协同油井监测与知识增强辅助分析系统——本科《石化信息工程》课程项目。

## Project Overview

系统以 Petrobras 3W 数据回放模拟树莓派边缘设备，完成实时遥测、云端存储、AI 推理、告警历史、实时 Web 可视化，以及受证据约束的 RAG + LLM 辅助诊断。它是教学与人工决策支持系统，不执行自动控制。

最终交付分支为 `codex/final-delivery`，与本次收尾后的 `main` 对齐。按用途阅读：

- [交付清单与复现边界](docs/final/delivery-manifest.md)：源码包内容、外置数据与模型、版本说明。
- [系统使用说明与课程演示方法](docs/final/user-guide-and-demo.md)：逐页操作、完整演示流程和问题处理。
- [简版答辩脚本](docs/final/demo-script.md)：8～10 分钟现场讲述提纲。
- [DeepSeek 接入说明](docs/final/deepseek-setup.md)：配置、费用、数据边界和已验证的报告 31。

## Architecture

实时链路：`Raspberry Pi Edge → MQTT/TLS → FastAPI → PostgreSQL / AI inference → WebSocket → Vue 3`。

辅助诊断：`已保存的推理结果 + 窗口统计 + 报警摘要 + 检索引用元数据 → 可选 LLM → 报告与系统生成的引用`。

详见 [系统架构](docs/final/system-architecture.md)。默认分析窗口为 180 秒，固定 7 个变量：`P_PDG`、`P_TPT`、`T_TPT`、`P_MON_CKP`、`T_JUS_CKP`、`P_JUS_CKGL`、`QGL`。

## Core Features

- 3W 真实油井数据回放与树莓派 Edge/Cloud 协同。
- MQTT 遥测、7 变量实时监控、PostgreSQL 历史记录与 Alarm/history。
- XGBoost active 与 TCN shadow 的时序推理边界，以及 WebSocket 驱动的 Vue 3 Dashboard。
- 基于受审阅静态知识清单的轻量关键词检索、系统生成的引用、DeepSeek 与通用 OpenAI-compatible LLM 接入，以及 `LLM analysis unavailable` 模板降级。
- 外部 LLM 接收窗口统计、实验性模型输出、报警摘要和引用元数据，不接收完整原始时序；系统不执行现场控制。

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

云端 API 的当前依赖目标是 **Linux amd64、Python 3.12**；前端构建使用 **Node.js 22**。API 的 PyTorch wheel 固定为 Linux x86_64，不能将默认 Apple Silicon 原生构建视为已支持。树莓派仅运行独立 Edge Agent。

源码不含证书、密码、数据集或模型二进制。先按 [部署说明](infra/README.md) 准备私网 MQTT/TLS、数据库环境变量及模型制品，再在源码根目录启动。以下用于独立环境，不用于直接重建已有生产实例：

```bash
# 仅在尚无 .env 时复制，之后填写部署值。
test -f .env || cp .env.example .env
docker compose --env-file .env -f infra/docker-compose.yml up -d --build
```

开发机能够访问 `localhost:8000` 的 API 时，使用 Vite 提供完整网页及 API/WebSocket 代理：

```bash
cd apps/web
npm ci
npm run dev
```

前端开发入口通常为 `http://localhost:5173`，以终端显示的端口为准；API 文档为 `http://localhost:8000/docs`。Compose 的 `127.0.0.1:8085` 仅提供静态页面，部署访问还需系统 Nginx 代理 `/api/` 和 `/ws`。

源码示例默认关闭 LLM。现有演示系统在 2026-09-22 已启用 `deepseek-flash` 并验证真实报告，2026-10-17 只读复查确认配置与保存的报告仍在；本次未再次调用供应商。浏览已有报告不产生新的模型调用。

## Testing

```bash
PYTHONPATH=apps/api python -m pytest apps/api/tests -q
PYTHONPATH=services/edge-agent python -m pytest services/edge-agent/tests -q
PYTHONPATH=ml python -m pytest ml/tests -q
cd apps/web && npm ci && npm run build
```

2026-10-17 本地复查：API **44 passed、9 skipped**，Edge **16 passed**，ML **17 passed**，前端 production build 通过。9 项集成测试本次未启动独立 PostgreSQL；2026-09-22 的适配镜像曾完整通过 **53 项 API 测试**。日期、环境及未重复验证项见[测试矩阵](docs/final/test-matrix.md)。

## Limitations

- 当前本地 3W 副本只有 55 个可读实例，旧 187-instance 协议无法复现。
- held-out `WELL-00014` 的 binary XGBoost 结果显示明显 domain shift，验证集高分不能代表跨井泛化。
- LLM 依赖可关闭的外部兼容 API，且只能引用 retriever 实际返回的资料。
- 本系统用于教学与辅助分析，**不构成工业故障诊断或自动控制系统**。

完整边界见 [最终限制说明](docs/final/limitations.md)。

## License

[MIT](LICENSE)
