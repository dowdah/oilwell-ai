# OilWell AI

边云协同油井监测与知识增强辅助分析系统——本科《石化信息工程》课程项目。

系统用 Petrobras 3W 数据回放模拟树莓派边缘采集，完成 MQTT/TLS 遥测、PostgreSQL 存储、XGBoost active / TCN shadow 推理、报警、实时网页，以及受证据约束的 DeepSeek 辅助诊断。系统用于教学与人工辅助分析，不执行油井现场控制。

## 课程交付入口

唯一交付分支为 `main`，精确版本以 `git rev-parse HEAD` 为准。2026-10-18 精简版保留完整运行源码、训练工具、测试和实验协议；旧研究提交保存在 `main` 历史中，不再另存备份分支或恢复包。

| 阅读目的 | 文档 |
| --- | --- |
| 使用七个页面、准备 8～10 分钟答辩、处理现场问题 | [系统使用说明与演示方法](docs/final/user-guide-and-demo.md) |
| 接入或维护外部模型 | [DeepSeek 接入说明](docs/final/deepseek-setup.md) |
| 理解系统数据流、知识库治理与引用边界 | [系统架构](docs/final/system-architecture.md) |
| 阅读测试证据、实验结果与限制 | [评估与限制](docs/final/evaluation-and-limitations.md) |
| 搭建独立实例 | [部署说明](infra/README.md) |
| 获取研究数据、重建训练环境 | [训练与数据说明](ml/README.md) |

现有演示入口：[OilWell AI](https://oil-well-ai-demo.dowdah.com/)。2026-09-22 曾完成真实回放和 DeepSeek 报告 31 验收，2026-10-17 做过只读复查；本次本地精简不连接生产或树莓派，也不代表再次验证外部服务。浏览已保存报告不会产生新的 LLM 调用。

## 系统与源码清单

实时链路：`Edge → MQTT/TLS → FastAPI → PostgreSQL / AI inference → WebSocket → Vue 3`。

辅助诊断：`已保存推理 + 七变量窗口统计 + 报警摘要 + 检索引用元数据 → 可选 LLM → 报告与系统生成的引用`。

默认窗口为 180 秒，变量固定为 `P_PDG`、`P_TPT`、`T_TPT`、`P_MON_CKP`、`T_JUS_CKP`、`P_JUS_CKGL`、`QGL`。XGBoost active 参与报警，TCN shadow 仅作同窗口对照；外部 LLM 不替代分类模型。

| 路径 | 交付内容 |
| --- | --- |
| `apps/api/`、`apps/web/` | 后端、前端与自动化测试 |
| `services/edge-agent/` | 数据回放、MQTT、持久化序列和单写者保护 |
| `infra/` | Compose、数据库、MQTT ACL 和 Nginx 示例 |
| `ml/`、`scripts/` | 特征、训练、评估、下载和数据审计工具 |
| `docs/final/` | 使用、接入、架构、评估四份课程文档 |
| `docs/knowledge-base/manifest.json` | 运行时使用的受审阅知识条目 |
| `docs/experiments/`、`docs/phase-b/` | 八份原有实验、审计与冻结协议 JSON，以及新建的演示资产清单 |

## 外置数据、模型与配置

源码包不含数据、模型二进制、真实配置或凭据。精简后本机仅保留四个演示 Parquet 样例及下列九个模型相关文件，来源、版本与 SHA-256 见 [演示资产清单](docs/experiments/demo-assets.json)。本地数据副本保留数据专用的 `dataset/LICENSE-CC-BY`（CC BY 4.0）、上游代码的 `LICENSE.md` 和引用说明 `CITATION.md`；再分发样例时需随附数据许可与引用说明。

| 材料 | 本地保留位置 / 接手要求 |
| --- | --- |
| 四个 3W 样例 | `ml/data/raw/petrobras-3w/dataset/`；文件清单见使用说明第 3.1 节；按许可单独提供，Edge 只读挂载 |
| XGBoost active | `ml/artifacts/current/`：`model_metadata.json`、`xgboost_model.json`、`metrics.json` |
| TCN shadow | `ml/artifacts/tcn-shadow/`：`model_metadata.json`、`tcn_model.pt`、`tcn_config.json`、`scaler.json`、`comparison.json` |
| 离线解释 | `ml/artifacts/explanations/explanation_manifest.json`；已修复井标识并重建四个首窗，须匹配模型版本、井和窗口，详见使用说明 |
| 数据库、MQTT、TLS | 接手者创建受限 `.env`、账号、ACL 和证书；不随源码传播真实部署配置 |
| DeepSeek API Key | 可选；接手者自行申请并写入服务器受限文件，源码默认关闭 LLM |
| 历史报告、PPT、演示录像 | 生产数据库及个人材料不打包；新实例不自带报告 31，PPT/录像需按教师要求准备 |

缺少 active 模型不能宣称具备模型报警能力；缺少 shadow 模型没有双模型对照；缺少同窗口解释会保留证据降级。模型交接需核对资产清单和元数据，重新训练产生的制品不能视为已验收版本。

历史数据审计对应 55 个实例，旧 187-instance 协议未在该副本复现；**当前四个演示样例不是完整训练集**。需要重新训练时，应重新取得协议要求的研究数据并核验哈希。被否决的二分类候选从未部署，结论保留在评估文档中。

## 独立运行与测试

云端 API 目标为 **Linux amd64 / Python 3.12**，前端构建使用 **Node.js 22**。当前 PyTorch wheel 指定 Linux x86_64，不能将 Apple Silicon 默认原生 API 构建视为已支持。树莓派运行独立 Edge Agent。

依赖缓存与本地虚拟环境不属于交付物。重新开发时先安装对应依赖；准备模型、私网 MQTT/TLS 和数据库配置后，按 [部署说明](infra/README.md) 启动独立环境：

```bash
# 仅在尚无 .env 时复制，填写部署值后启动。
test -f .env || cp .env.example .env
docker compose --env-file .env -f infra/docker-compose.yml up -d --build
```

开发机能访问 `localhost:8000` 的 API 时，可在 `apps/web` 运行 `npm ci`、`npm run dev`，通过 Vite 代理使用完整网页。Compose 的 `127.0.0.1:8085` 仅提供静态页面，部署访问仍需 Nginx 代理 `/api/` 和 `/ws`。

```bash
PYTHONPATH=apps/api python -m pytest apps/api/tests -q
PYTHONPATH=services/edge-agent python -m pytest services/edge-agent/tests -q
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=ml python -m pytest ml/tests -q
cd apps/web && npm ci && npm run build
```

2026-10-18 SHAP 修复后：API **49 passed、9 skipped**，Edge **16 passed**，ML **33 passed**；四个本地首窗已验证解释匹配。ML 验证使用上面的单线程设置。此前同日精简阶段的 Web 构建通过，本次未改前端、未重复构建，也未部署生产。2026-09-22 DeepSeek 适配镜像曾通过完整 **53 项 API 测试**；不同日期和环境不能合并成一次验收。数据库测试配置及完整记录见 [评估与限制](docs/final/evaluation-and-limitations.md)。

## 打包与版本恢复

课程源码包固定为 Git 忽略目录中的 `dist/oilwell-ai-course-delivery.zip`，仅打包 `main` 的受版本控制文件：

```bash
mkdir -p dist
git archive --format=zip --output=dist/oilwell-ai-course-delivery.zip main
```

不要直接压缩整个开发目录。ZIP 不含 Git 历史、数据、模型、依赖、密钥或生产数据库。已删除的历史源码和文档可从 Git 历史查阅；此次删除的未受版本控制研究数据与实验模型不再承诺本地可恢复。

## License

项目源码采用 [MIT](LICENSE)。3W 数据的许可和引用要求单独适用，不能用源码许可证替代。
