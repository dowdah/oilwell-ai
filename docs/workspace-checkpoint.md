# Phase A 前工作区检查点建议

分析时间：2026-09-13T01:18:08+08:00（Asia/Shanghai）。

本次只新增本文；不暂存、不提交、不修改代码、不删除文件、不 reset，不运行训练、构建、数据库或 MQTT 验收。本建议等待用户确认后才执行。

## 1. 对照迁移基线的结果

- 当前分支：`codex/phase-1-5-completion`。
- 当前 HEAD：`b06d6566ef5731657dbf36c94b1785db6bbfbea5`，`docs: record migration baseline`。
- [migration-baseline.md](migration-baseline.md) 已单独提交；本次创建本文之前仍有 44 个已跟踪修改、53 个未跟踪文件，共 97 个，路径与基线清单一致。
- 暂存区为空。分类为：工程与根目录工具 38 个、ML 23 个、文档 36 个。
- 本次读取 97 个文本文件，对 Python/JSON 进行静态解析，并检查导入依赖、差异和常见敏感信息模式；不把静态检查等同于功能测试通过。

## 2. Checkpoint 方案比较与建议

| 方案 | 明确范围 | 保护能力与代价 |
|---|---|---|
| A：提交全部当前功能代码 | 61 个非 docs 文件；不含 36 个实验/验收文档和所有忽略资产 | 工程及研究源码保存完整，但实验决策、失败证据仍未受 Git 保护；训练入口入库不代表执行训练 |
| B：仅提交工程闭环所需代码 | 下文 E 组 45 个文件；含必要 ML 支撑和测试依赖，不含 52 个其余文件或本地制品 | 是本次整文件、不改代码条件下建议的最小工程范围；仍有 52 个历史文件未保护 |
| C：分两笔保存工程与冻结研究（推荐） | C1 保存 E 组 45 个文件及本文；C2 保存 R 组 52 个历史源码/实验/验收文件 | 最终保护当前全部 97 个变更，工程修复与研究历史分别可审阅、可追溯；不提交原始数据、权重或私有材料 |

推荐 C。它满足“保护当前工作区”这一目标，又不把冻结实验变成 Phase A 开发内容。两笔提交都只是保存当前内容，不修改功能；不是部署、合并或验收通过。若只选 B，应明确接受研究源码和证据仍未形成检查点这一缺口。

建议提交消息（仅建议，本轮不执行）：

1. C1：`chore: checkpoint existing engineering state before phase A`。
2. C2：`chore: preserve frozen experiment code and evidence`。

本文为新增第 98 个文件，不计入原有 97 个；C1 为 45 个既有文件 + 本文，C2 为 52 个既有文件。已经提交的 migration-baseline.md 不重复修改。

### 最小工程范围的依赖理由

- `router.ts` 与未跟踪 `HistoryView.vue` 必须共同保存；Edge 的 main/config/Compose 与未跟踪 `sequence.py` 也必须配套。
- API 当前 TCN 适配器导入 `tcn_data.py`，它新导入 `windows.py`，后者引用 `manifest.py`。在 Phase B 之前不能按“以后只用 XGBoost”提前移除这条现有依赖。
- `ml/tests/test_windows.py` 同时覆盖基础窗口与实验特征，导入 `features_v2.py`、`preprocessing.py`，并动态加载 `prepare_demo_windows.py`。为不修改已验证测试、不拆补丁，整文件保留这些依赖；保留不等于开启研究优化。
- 根 pytest 配置会收集 ML 测试；最小范围保留必要声明和对应测试，其他原本已跟踪且未纳入的文件使用 HEAD 内容。这个组合尚未在独立快照中运行测试，不能沿用脏工作区的“74 项通过”作为子集通过结论。
- C1 是实际可审阅的整文件最小建议，并非数学意义上的最少行数；进一步缩减会需要拆改文件或测试，违反本轮仅保护现状的目的。

## 3. 应提交文件列表（须确认后执行）

`E`＝建议工程最小范围 / C1；`R`＝建议第二笔冻结历史 / C2。`M`、`??` 是创建本文前的 Git 状态。当前 97 个文件中没有发现必须因已确认凭据而永久排除的文件；风险与限制见第 6 节。

### E 组：45 个文件

| 状态 | 文件 | 提交理由 / 用途 |
|---|---|---|
| `M` | `.dockerignore` | 排除本地证据、数据与模型进入构建上下文 |
| `M` | `apps/api/Dockerfile` | 保留已使用的依赖安装与构建调整 |
| `M` | `apps/api/app/database.py` | BIGINT、报警恢复与诊断审计迁移 |
| `M` | `apps/api/app/diagnostics.py` | 已有模板诊断的证据与降级修复；不启动新 RAG 开发 |
| `M` | `apps/api/app/inference.py` | 严格窗口、异步推理隔离、模型线程限制 |
| `M` | `apps/api/app/main.py` | 历史接口、设备离线、诊断及报警接口调整 |
| `M` | `apps/api/app/models.py` | 序列号、报警恢复与诊断审计字段 |
| `M` | `apps/api/app/mqtt.py` | MQTT 链路调用异步推理 |
| `M` | `apps/api/app/realtime.py` | WS 日期序列化与窗口缓存处理 |
| `M` | `apps/api/app/schemas.py` | 七变量与时间/序列号输入约束 |
| `M` | `apps/api/app/services.py` | 入库、心跳、报警确认/恢复状态逻辑 |
| `M` | `apps/api/requirements.txt` | API 当前依赖；仍含旧 TCN CPU 依赖，Phase B 才迁移 |
| `M` | `apps/api/tests/test_contract.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `M` | `apps/api/tests/test_diagnostics.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `M` | `apps/api/tests/test_inference.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `M` | `apps/web/Dockerfile` | 已有前端构建调整 |
| `M` | `apps/web/src/App.vue` | 已有导航与页面入口 |
| `M` | `apps/web/src/api.ts` | 历史与诊断接口客户端 |
| `M` | `apps/web/src/router.ts` | 路由懒加载与 History 路由，需同时提交新页面 |
| `M` | `apps/web/src/views/AlarmsView.vue` | 已有报警显示修复 |
| `M` | `apps/web/src/views/DiagnosticsView.vue` | 已有诊断交互，不代表真实 LLM 已接入 |
| `M` | `apps/web/src/views/EdgeView.vue` | 命令确认、拒绝与设备状态展示 |
| `M` | `apps/web/src/views/MonitorView.vue` | 七变量曲线、重连、限频与回放时间重置 |
| `M` | `ml/oilwell_ml/manifest.py` | 窗口模块依赖的列/标签定义及质量检查 |
| `M` | `ml/oilwell_ml/tcn_data.py` | 现有 TCN 适配器导入的 scaler 与数据契约 |
| `M` | `ml/requirements.txt` | 当前数据/测试依赖声明 |
| `M` | `ml/scripts/prepare_demo_windows.py` | 窗口测试动态导入的严格窗口准备入口 |
| `M` | `ml/tests/test_tcn_data.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `M` | `services/edge-agent/docker-compose.yml` | 持久化 sequence 卷；含原有设备目录默认值 |
| `M` | `services/edge-agent/edge_agent/config.py` | 持久化序列号配置 |
| `M` | `services/edge-agent/edge_agent/main.py` | 命令回执、线程代际和回放控制 |
| `M` | `services/edge-agent/edge_agent/replay.py` | 真实时间戳、七变量连续回放检查 |
| `M` | `services/edge-agent/tests/test_replay.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `??` | `apps/api/tests/test_postgres_integration.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `??` | `apps/api/tests/test_realtime.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `??` | `apps/web/.dockerignore` | 构建上下文排除规则，与对应 Dockerfile 配套 |
| `??` | `apps/web/src/views/HistoryView.vue` | 新增历史页，与 router.ts 配套 |
| `??` | `ml/oilwell_ml/features_v2.py` | 新窗口测试引用；为保持整文件提交保留实验特征，不启用上线 |
| `??` | `ml/oilwell_ml/preprocessing.py` | 新窗口测试引用的变换；保留源码不执行增强或训练 |
| `??` | `ml/oilwell_ml/windows.py` | tcn_data 与回放窗口工具共同依赖的新窗口模块 |
| `??` | `ml/tests/test_windows.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `??` | `pytest.ini` | 统一 API/ML/Edge 收集范围，不能只凭当前脏工作区验证子集 |
| `??` | `scripts/check_local_mqtt_chain.py` | 本地 MQTT/命令/数据库验证脚本，保存但不运行 |
| `??` | `services/edge-agent/.dockerignore` | 构建上下文排除规则，与对应 Dockerfile 配套 |
| `??` | `services/edge-agent/edge_agent/sequence.py` | 新增原子序列号租约持久化，与代理配置配套 |

### R 组：52 个文件

| 状态 | 文件 | 提交理由 / 用途 |
|---|---|---|
| `M` | `docs/experiments/3w-eda-summary.json` | 历史数据质量/分布汇总，保留失败分析依据 |
| `M` | `docs/experiments/3w-instance-selection.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `M` | `docs/experiments/3w-manifest.json` | 公开 3W 文件清单、哈希与质量统计；非原始逐点数据 |
| `M` | `docs/experiments/3w-split.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `M` | `ml/oilwell_ml/split.py` | 历史井级隔离与实例展开修复，归入冻结研究检查点 |
| `M` | `ml/scripts/generate_explanations.py` | 既有解释制品生成修复，保存历史，不提前实施 Phase C |
| `M` | `ml/scripts/report_eda.py` | 真实标签窗口 EDA 工具 |
| `M` | `ml/scripts/select_instances.py` | 历史实例筛选与展开入口 |
| `M` | `ml/scripts/train_baselines.py` | IF/XGBoost 二分类与四分类训练入口，保存但不执行 |
| `M` | `ml/scripts/train_tcn.py` | TCN 历史离线训练入口，保存但不执行 |
| `M` | `ml/tests/test_split.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `??` | `docs/experiments/3w-expanded-manifest.json` | 公开 3W 文件清单、哈希与质量统计；非原始逐点数据 |
| `??` | `docs/experiments/3w-observation-selection.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `??` | `docs/experiments/3w-supplement-manifest.json` | 公开 3W 文件清单、哈希与质量统计；非原始逐点数据 |
| `??` | `docs/experiments/additional-data-request.md` | 旧数据需求记录，保留历史，不阻塞新方向 |
| `??` | `docs/experiments/constant-signal-audit.json` | 历史数据限制、质量或来源分析，冻结保留 |
| `??` | `docs/experiments/data-card.md` | 历史数据限制、质量或来源分析，冻结保留 |
| `??` | `docs/experiments/domain-augmentation-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/experiments/dynamics-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/experiments/expanded-normal-training/decisions.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `??` | `docs/experiments/expanded-normal-training/selection.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `??` | `docs/experiments/expanded-normal-training/split.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `??` | `docs/experiments/expanded-training-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/experiments/expanded-training/3w-eda-summary.json` | 历史数据质量/分布汇总，保留失败分析依据 |
| `??` | `docs/experiments/expanded-training/coverage.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `??` | `docs/experiments/expanded-training/decisions.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `??` | `docs/experiments/expanded-training/selection.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `??` | `docs/experiments/expanded-training/split.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `??` | `docs/experiments/interrupted-experiments.json` | 中止实验记录，防止误计为完成 |
| `??` | `docs/experiments/normal-only-sources-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/experiments/normal-segment-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/experiments/phase-1-5-results.json` | 候选指标与混淆矩阵汇总，冻结，不作为新系统门禁 |
| `??` | `docs/experiments/relative-window-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/experiments/runtime-environments.json` | 历史环境与架构信息，不是生产性能证据 |
| `??` | `docs/experiments/supplement-coverage.json` | 样本选择、井级划分或排除决策证据，冻结保留 |
| `??` | `docs/experiments/tcn-interleaving-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/experiments/well-balanced-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/experiments/window-shape-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/experiments/zero-channel-protocol.md` | 已执行研究协议与限制，冻结，不恢复优化任务 |
| `??` | `docs/knowledge-base/retrieval-evaluation.json` | 现有合成检索契约结果，不代表真实模型或 LLM 验收 |
| `??` | `docs/knowledge-base/review-packet.md` | 历史来源审阅材料，人工复核仍待完成 |
| `??` | `docs/knowledge-base/source-access-check.json` | 已有知识来源访问与哈希记录 |
| `??` | `docs/phase-1-5-acceptance.md` | 历史工程/四分类验收记录；旧门禁已被用户新方向替代 |
| `??` | `ml/oilwell_ml/evaluation.py` | 离线指标、时延及哈希辅助函数 |
| `??` | `ml/oilwell_ml/weighting.py` | 类别/井权重与零通道试验，冻结 |
| `??` | `ml/requirements-acceptance.lock.txt` | Mac 历史训练/测试环境快照，不当作 Linux 部署锁文件 |
| `??` | `ml/scripts/extend_training_selection.py` | 保持 held-out 记录的数据扩展工具 |
| `??` | `ml/scripts/select_observations.py` | 按真实观察标签选择窗口 |
| `??` | `ml/tests/test_explanations.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `??` | `ml/tests/test_weighting.py` | 对应模块回归测试；保留测试代码，本次不运行 |
| `??` | `scripts/select_additional_normal.py` | Normal-only 历史数据补充工具，冻结 |
| `??` | `scripts/summarize_phase_1_5_experiments.py` | 14 个已完成候选结果汇总入口，冻结 |

## 4. 不应提交文件列表

以下均不属于上述 97 个待提交文本文件。本轮没有更改忽略规则；任何方案都不使用强制加入或整体暂存。

| 路径或模式 | 原因 | 本轮观察 |
|---|---|---|
| `ml/data/raw/petrobras-3w/` | 上游原始数据及其本地 Git/缓存，不是工程源码 | 目录存在，已忽略 |
| `ml/data/raw/phase15-expanded/` | 扩展原始 3W 文件；公开来源也不意味着应入工程 Git | 目录存在，已忽略 |
| `ml/artifacts/` | 模型权重、解释制品与运行时元数据；代码提交不包含模型载荷 | 93 个本地文件，已忽略 |
| `docs/.local/` | 私有接入资料、原始验收证据、日志、截图、回放 payload 与临时脚本 | 81 个文件，已忽略；不把全部内容复制到公开文档 |
| `.env`、`.env.*`（模板例外） | 可能含服务地址、账号、密钥 | Git 忽略规则存在；本轮检查的 `.env`、`.env.local` 未发现，不推断其他环境没有秘密 |
| `infra/certs/`、`infra/mosquitto/passwords/` | TLS 密钥、认证资料 | 忽略规则存在；本轮对应路径未发现 |
| `.venv/`、`__pycache__/`、`.pytest_cache/` | 可重建依赖与缓存 | 保持忽略 |
| `apps/web/node_modules/`、`apps/web/dist/` | 依赖与构建产物 | 目录存在，保持忽略 |
| `*.parquet`、`*.pt`、`*.pkl`、`*.joblib` | 原始数据或模型序列化文件 | 忽略规则存在 |

若选择 B，R 组 52 个文件也不进入该笔工程提交，但必须保留在原位置；“不进入本笔”不表示应删除或永不保存。若选择 C，这些非敏感文本应由 C2 保存。

## 5. 实验资产与本地制品

### 可入库的研究文本资产

- 数据与协议：`docs/experiments/` 中的 32 个变更文件，包括初始/补充/扩展清单、selection/split/decisions、质量审计、失败分析和冻结协议，完整路径见 R 组。
- 研究源码：R 组 16 个非 docs 文件，涵盖数据选择、训练、评估、权重、解释生成、测试与 Mac 依赖快照；部分基础研究依赖因现有运行时/测试导入放在 E 组。
- 验收与检索证据：`docs/phase-1-5-acceptance.md` 和 3 个 `docs/knowledge-base/` 文件；其中人工审阅待完成，旧四分类门禁已被新方向替代。保存这些文本不代表执行其中的旧后续指令。
- JSON 清单包含公开数据相对路径、哈希、标签、统计与指标，不是原始逐点遥测。最大清单约 2.25 MB，属于可审阅文本；数据公开性和文件规模均不能替代内容检查。

### 本地制品目录清单

| 目录 | 文件数 | 逻辑字节数 | 用途 |
|---|---:|---:|---|
| `ml/artifacts/current/` | 6 | 2201604 | 原有 XGBoost 四分类、二分类及 IF 制品 |
| `ml/artifacts/explanations/` | 2 | 6552 | 离线 SHAP 与解释清单 |
| `ml/artifacts/phase-1-5-augmented/` | 6 | 3444067 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-candidate/` | 11 | 2512304 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-dynamics/` | 6 | 2271856 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-expanded/` | 6 | 2801458 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-expanded-mps/` | 5 | 232547 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-expanded-normal/` | 6 | 2775488 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-interleaved/` | 5 | 241201 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-normal-segments/` | 11 | 2620507 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-relative/` | 6 | 2505599 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-shape/` | 6 | 4868493 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-well-balanced/` | 6 | 3003904 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/phase-1-5-zero-channel/` | 6 | 11940364 | 冻结实验候选、模型/指标/元数据 |
| `ml/artifacts/tcn-shadow/` | 5 | 212603 | 原有 TCN 权重、配置、scaler 和对照 |

[migration-baseline.md](migration-baseline.md) 已列出 91 个模型/指标文件的 SHA-256。另有以下 2 个解释文件，共构成本轮发现的 93 个制品文件：

- `ml/artifacts/explanations/explanation_manifest.json`：SHA-256 `fe8f74220e500e494d7d51743894fa4da31bea586fd5ac441104a08f70047ccc`。
- `ml/artifacts/explanations/xgb-tree-shap.json`：SHA-256 `433c0630e1c0597b316fdea7d89148873f66e00a783924c19b003d77ce8667bc`。

本地原始数据目录合计 1198 个文件、557806797 逻辑字节；包含辅助文件和嵌套 Git 内容，不等于数据集实例数。硬链接可能重复计数，逻辑字节数不是物理占用。

### Git 检查点的保护边界

提交源码和记录不会备份上述原始数据、权重或 `.local` 证据；文件哈希只能验证，不能恢复内容。它们本轮保持原样。如需要完整灾备，应另行确认受限访问的离线备份范围，避免把私有接入资料和可分享研究资产混装；本轮不创建备份。

## 6. 可能包含敏感信息的文件与检查结果

| 文件/范围 | 风险 | 本轮结果与提交建议 |
|---|---|---|
| `services/edge-agent/docker-compose.yml:15` | 默认挂载路径暴露设备用户名与目录约定 | 检测到 `/home/<user>/oilwell-data` 形态，且该默认值已在 HEAD 中存在；非本次新增凭据。保留现状可纳入 E 组，未来公开部署模板治理单独确认 |
| `apps/api/tests/test_postgres_integration.py` | 读取测试数据库连接环境变量；脚本包含建表/删除测试 schema | 不含硬编码生产连接串；有本机地址和专用测试数据库限制。本轮只读，不执行；测试代码可纳入 E 组 |
| `scripts/check_local_mqtt_chain.py` | 会操作本地 MQTT、回放命令和数据库，不是只读探针 | 使用 loopback 端点；未发现硬编码真实凭据。可以保存源码，本轮禁止运行 |
| `docs/experiments/*manifest*.json`、selection/split/decisions | 数据路径、井标识、时间范围、标签与统计可能被误认为私有现场数据 | 目前是公开 3W 研究元数据；未命中私人主目录或私网地址模式，纳入冻结文本证据，不能泛化为生产数据公开授权 |
| `docs/experiments/runtime-environments.json`、`ml/requirements-acceptance.lock.txt` | 环境指纹、依赖源可能携带机器或认证信息 | 本轮看到版本/架构与公开依赖信息，无凭据模式命中；可入库，不能当作服务器实际运行快照 |
| `docs/knowledge-base/` 三个新文件 | 资料许可、引用状态和审阅结论 | 保留“待人工确认”状态，不扩充为已授权生产资料或已完成 RAG 的声明 |
| `docs/.local/access-runbook.md` | 潜在主机地址、账号和接入操作信息 | 仅确认路径存在，不读取/复制内容；保持忽略，不纳入任何建议提交 |
| `.env*`、证书、MQTT 认证目录、`.local` 日志/回放文件 | 可能含凭据、地址、真实载荷 | 不对其作“无秘密”保证，不提交；本轮不打开接入秘密文件 |

本轮对 97 个变更文本进行凭据赋值、带认证 URL、私钥头、常见供应商 token、私人主目录与私网地址模式扫描；唯一命中为上述已有设备目录路径。未命中不等于完备安全认证，尤其无法识别任意格式秘密或全部业务敏感信息。任何实际提交仍须检查其精确 staged diff；本轮没有暂存。

## 7. 确认后执行的边界

建议确认 C（两笔保存全部 97 个既有变更），或明确选择 B（只保护 E 组）。本轮到本文创建与只读验证为止。

后续获确认后，先重新核对 HEAD、文件清单和下列哈希，检查是否出现新修改；逐路径准备选定范围并核对 staged diff。保存检查点不启动服务、不迁移数据库、不训练、不推送、不合并。各提交完成后核对剩余工作区，保证未纳入文件原样保留。

若要验证 B/C1 的独立可运行性，需要另行在仅含该提交内容的隔离工作区回归；不能在仍含 R 组未提交文件的当前目录宣称验证了最小提交。Phase A 的执行方案应说明测试依赖、数据库写入和回放影响，再经确认。

取消本文只需在另行授权后删除本文；本轮不删除。未来检查点本身不改变工作区功能；若需撤销 Git 检查点，应先保存后续工作并单独设计操作，不用 reset/clean 作为默认“回滚”。

## 8. 本轮 97 个文件的内容指纹

以下 SHA-256 固定本次建议分析的具体内容，不包含秘密值或模型载荷。它们不是提交，也不能代替内容备份。

| 文件 | SHA-256 |
|---|---|
| `.dockerignore` | `773acacd048de38f153e0ead1e5eab7af431797759143465a5a4a71289b77df0` |
| `apps/api/Dockerfile` | `3c76c41a91834761a8e10aa3b513500ac879366806204a094e1b8adbcdae4fad` |
| `apps/api/app/database.py` | `598bcff5506d73d6a2f0a39335937c68f9d0a1b57250f5a28a7149e10086e203` |
| `apps/api/app/diagnostics.py` | `61d9704f11e7940f445eecc636c1b589efe4415de5b5ceba83a16390311c2108` |
| `apps/api/app/inference.py` | `dd8abd2ef0d8ab68847dc6a185c33159b260ecd7c88e8fcd098fb369e04b504d` |
| `apps/api/app/main.py` | `fc4261eba7565ec05dd2cb70f186828f38f821b15b73cda58654431e9fceb4fc` |
| `apps/api/app/models.py` | `bcd2bdf722fd09515dee5d5ed77e7463e950c743c6c7591627cd3112d65626b6` |
| `apps/api/app/mqtt.py` | `60965ce9bee962dd571743905d6da2167202ca443e2fec78e9d89df0058a657c` |
| `apps/api/app/realtime.py` | `3eadf77726efde6bc1bf904ae53e7b3c0bd9dc62e7a3389534faec085f26ec4d` |
| `apps/api/app/schemas.py` | `6ffa8e1bdcc308ace6d940c4f6661c1518275f76bfeaedbb54c4fa9bf3c53591` |
| `apps/api/app/services.py` | `be6574a473a9f3506fe54a6ca561998f324b642550e8eee14fdd717d52aac1e5` |
| `apps/api/requirements.txt` | `2f3ba59368e71f05c28f95b2be9a1460fe51ae2ed938e8ea0fd65ac04f777bdb` |
| `apps/api/tests/test_contract.py` | `fb9f1641ca2dff41bd618baf174ae68f899d54f4cf5d606eeb7d5ee2c7e4c31b` |
| `apps/api/tests/test_diagnostics.py` | `9871ca43faf7c7102ac7d861e83e299e294bc9b725403f7e805dc970ed274032` |
| `apps/api/tests/test_inference.py` | `6bca76b075b84d6e8bf169cff05313e1d8d3d1c64a83af195878d6b68365da5a` |
| `apps/web/Dockerfile` | `8ffea9ea56039ed566eaf559402e59d8afcb68216a002b7355486e5c23f7e081` |
| `apps/web/src/App.vue` | `f9bfa4eeed1ad68d807962dddc7268a82a8ff66245c7dc1ade1b37588c92b163` |
| `apps/web/src/api.ts` | `880a2f8d758c75ebef0756cdaff7febe7b8d200b6987e1716a0724ff829aeb61` |
| `apps/web/src/router.ts` | `2981b7430b083719df14f9e6a29d982d294877776850e361a4145070183a8365` |
| `apps/web/src/views/AlarmsView.vue` | `c9ad1eb94917fb5d31a5bd865ee7b93dc17f2210c5ae0cefe6e3930b8500e812` |
| `apps/web/src/views/DiagnosticsView.vue` | `80e55118f242b265a69fef6e59bfbaceff9fb837023904c28435e8b0c5238971` |
| `apps/web/src/views/EdgeView.vue` | `cf23d4967181db7627292ab8bfd1f4beda22402de32c44e26da74a37d5bea874` |
| `apps/web/src/views/MonitorView.vue` | `25fc58ce15223ec52d69dc5be5d3858c6e4e89ee246eee744c2935a6757d4d89` |
| `docs/experiments/3w-eda-summary.json` | `69ad08548d664ccdbbb5186e3fc750cbeaa64da7b4d9d84aa3aa3da19e137384` |
| `docs/experiments/3w-instance-selection.json` | `125df8145d78aa4e00d0bf5ee5db4c1c8ef206d45962c2c2778ca9a701776c25` |
| `docs/experiments/3w-manifest.json` | `05f60ccddccfe6538329e37924994182017ac9ec576a17480d826246163f8107` |
| `docs/experiments/3w-split.json` | `9e868500e579f17d3c37f9990bf72d04ad98da744aa496cab6ef774733f48271` |
| `ml/oilwell_ml/manifest.py` | `c84ed79b3c0ba1b65a0833a0ca33af2d79b17213069fa983e293bc438789466f` |
| `ml/oilwell_ml/split.py` | `7a1201e95be8f79abb7a866de0302ef0a097e0a7359fda028379dd252006612b` |
| `ml/oilwell_ml/tcn_data.py` | `97ccef368555c3984ecc9b25b2cda0d2545ab23984a16f70fd1a1e795b05c68f` |
| `ml/requirements.txt` | `ae49b7c2d604fc6e1d1b94a6e4eb565b903020c1f9cf01c6932a2890c358fe86` |
| `ml/scripts/generate_explanations.py` | `e8b2f5b03486deb09590b07abbc9b60e7f457e60e803c6a1b1a522c542ade12f` |
| `ml/scripts/prepare_demo_windows.py` | `3eb41f912b62035037f489a4aa07def3cbe634ae414153980bd28a98ba934416` |
| `ml/scripts/report_eda.py` | `0b25fb52ba2b5e785d39a4b1b8cae59403061bdac336eb1c29373252f34cc17c` |
| `ml/scripts/select_instances.py` | `5917897beb9f80bc0916d98d850a8b8fddd9aa5b328f0696ec9dfe53b1f96d75` |
| `ml/scripts/train_baselines.py` | `7d8ab8318dc447eeb30e26c40f85e1d4724c5cc2e8c2a5090c3eeb0e04aaf5c1` |
| `ml/scripts/train_tcn.py` | `a3a7ad88c89020e899748bba4f10b2389298d17a431b05491993e55a5d68bafc` |
| `ml/tests/test_split.py` | `2974e625d78cefe85832837f2f1a7859542ed848cab2448c70455661d7b8abd2` |
| `ml/tests/test_tcn_data.py` | `9e82306a3c9787244a33e5fde09b6af8137a4e585f94bbfe88ada660da14a7a0` |
| `services/edge-agent/docker-compose.yml` | `6b50e80831551f30c4c437634007a4b1ba0cc397350632f3f53f4ef750f69194` |
| `services/edge-agent/edge_agent/config.py` | `7f4bd31bc8ac5a23f5bbd8983de36ecc788d7c479eb4fe07efb577dd566cc2a6` |
| `services/edge-agent/edge_agent/main.py` | `81677b2398af9b92c2e7c6cc6f8b95af35075c8294c8c10b9f3399595e6704ea` |
| `services/edge-agent/edge_agent/replay.py` | `21e5f51660827d9bd283e81719306fbf5f243edeb22ced8cfdfe545fc4ad2cc6` |
| `services/edge-agent/tests/test_replay.py` | `b28042424528e18373fed5cd1acb0d6f12edab1cdfa2265f8e388de10fc4e7e8` |
| `apps/api/tests/test_postgres_integration.py` | `e554b359fa784ebc9b123d2bf9fb556f1fb9f4f323732e4a33e4210270bf82b0` |
| `apps/api/tests/test_realtime.py` | `60c13dbaa4e7e45cea31a844f8a96237df8d979e249037d5d2fbf52e13e792a1` |
| `apps/web/.dockerignore` | `f090888e234765c2f5493bdd35ba578215b2ce8530a8a2261dc99bae7494eecd` |
| `apps/web/src/views/HistoryView.vue` | `d3c8f129c151ee8eec8096baa20e8debdc3ad93908ba209776aa1ba10d9c6ecf` |
| `docs/experiments/3w-expanded-manifest.json` | `6633963ce85a2d6cc73d6fb66cabd5482f0e5d7f82b9d0430dcb9cffb3f61d65` |
| `docs/experiments/3w-observation-selection.json` | `ea7027682614ac8d7e5a0fbc42bc1da24801ab8d7f37e223e0f6291699bec87f` |
| `docs/experiments/3w-supplement-manifest.json` | `3c9244ede37a8e400924e048db04a823125103cd5ba41b6098a41203db254905` |
| `docs/experiments/additional-data-request.md` | `461bd9bfc08a6cc8b0f9fb55360db1832b0a3475316827ea6ee7919b802ac48d` |
| `docs/experiments/constant-signal-audit.json` | `5f989927dfdb78ee5f9b180c23796c186e1bebf476a7054e8960b05e1f1b5467` |
| `docs/experiments/data-card.md` | `b20451c7cac5714cf2dc4c6a4fe23da4b71e704b4914adbb0da6e7d7d516106b` |
| `docs/experiments/domain-augmentation-protocol.md` | `9fb9bd60ded09733ec11924220e0552896a25d1ee0d03eb6d854e5d13e674e1e` |
| `docs/experiments/dynamics-protocol.md` | `55960c4107d4b77c3dd5a9eccb388037d85222f67646bcad798a3ef88b3cdb11` |
| `docs/experiments/expanded-normal-training/decisions.json` | `7b788807d61e28770a3b89e767302457ddd242dcd8c18679b9ef5ce6a9962c25` |
| `docs/experiments/expanded-normal-training/selection.json` | `c320f66d0cc0f83ca0776a69f16fe5da118260461d430be56c28a63387b3842c` |
| `docs/experiments/expanded-normal-training/split.json` | `59d5451f3572f6a91b941e67f4fe5259effd057734d14a3e0ebda60d738528cd` |
| `docs/experiments/expanded-training-protocol.md` | `f83fab071f52d80a3f39741d8cd58cd9039e936b224217c24aeb9e308ad5c107` |
| `docs/experiments/expanded-training/3w-eda-summary.json` | `a11b66aca924de97ea54a1d127628e3b996e5d3de070d85d0b187366e46cf93a` |
| `docs/experiments/expanded-training/coverage.json` | `606c9a38104b18945742d11a8b0012ee8a9912c58d5cbf90c4df653cf237fcf3` |
| `docs/experiments/expanded-training/decisions.json` | `5e49a9a687276e5d012c571490325f583c17f02497f2dcdb5c3c58249ba8555c` |
| `docs/experiments/expanded-training/selection.json` | `cd9c3184b0f5e32f00cff821818c40597c15df914fd8056e56358c186e007bb0` |
| `docs/experiments/expanded-training/split.json` | `557bd6ccb4a6b9035220afd1331b3de6e237fb4487f77e673cd8f52d4d9e7352` |
| `docs/experiments/interrupted-experiments.json` | `ee86f840370e90f52bf631ab59469a4c7222350702009d2feb5f92ead2692781` |
| `docs/experiments/normal-only-sources-protocol.md` | `3bbcbca7a136e9e227bbdcfde3350085b1158de0352c10b098e5cf4e2e579550` |
| `docs/experiments/normal-segment-protocol.md` | `6c4c125beb96787848a904564790e048d07caa9a0d8f1649d1462320730a3756` |
| `docs/experiments/phase-1-5-results.json` | `4ef1f09598ff519a8c79a1003806171a11c690bf2b3525ab1c7c7614ccdb5e61` |
| `docs/experiments/relative-window-protocol.md` | `1b3189f0a1270a7ebeeac6c2222c99f77cbc0136b8a16589d30def4300e9b5d3` |
| `docs/experiments/runtime-environments.json` | `251da6015059fa53b13081626a9e2d39b2807c1c8e36a5aa74103896159ba36a` |
| `docs/experiments/supplement-coverage.json` | `84f1f2711fd3b0ada402688fa53e058a2dcf488343c6a25e474a4803e6241e60` |
| `docs/experiments/tcn-interleaving-protocol.md` | `0ad3eee4e9517755cfdd513fc62a6194a6b09382fc30f719a07b8c006e586c9f` |
| `docs/experiments/well-balanced-protocol.md` | `3272e67999460c86b73e73c1d418d383778b74ee7f398b20bafacd585dd97552` |
| `docs/experiments/window-shape-protocol.md` | `786cbb104980597733a186c754dec964eb3f9b792542d830363cc95fbc125260` |
| `docs/experiments/zero-channel-protocol.md` | `f19086bc34ca498d6471a8bba28dbac02d40a6d027d518b94ad40a9c6a0ab99c` |
| `docs/knowledge-base/retrieval-evaluation.json` | `435697dfd532816746e872d08ddec58888a4fddfb16e1923a11692eabe1e3689` |
| `docs/knowledge-base/review-packet.md` | `8460905021d7b28d95f3106b7074728b2e48eb573cdede621f2c01a2f359ec46` |
| `docs/knowledge-base/source-access-check.json` | `ad1036407b03d91766c7137b4cb967cdce3900801065d10ddfd5b65f0d358882` |
| `docs/phase-1-5-acceptance.md` | `fa9b10c66b6557dc9f048866e661c7e944f3e611578abbeac2bbde7c0254a0b8` |
| `ml/oilwell_ml/evaluation.py` | `05868775ff49bf032d1a094fd77b973cf999be10f3ddd278ddfba664f0c95de6` |
| `ml/oilwell_ml/features_v2.py` | `3d584b009f7b133c372724ce31113220886eefce3802eb15264b6a83c90812f2` |
| `ml/oilwell_ml/preprocessing.py` | `32e4f9b5e97800c7dad4812291e92777813f0ee406af6c4149dc393b2b10ef34` |
| `ml/oilwell_ml/weighting.py` | `3d71c30744e92c44390c772a33526f02af525339ec759e344e3bef77d879e604` |
| `ml/oilwell_ml/windows.py` | `32290b3ac7e04af75048fe4155ccd7d70d8a54c5efb10735ae66005eae10987b` |
| `ml/requirements-acceptance.lock.txt` | `b1834f007888d9ee793d072f349dcab28eb2581de256d93647d361a8df71a39a` |
| `ml/scripts/extend_training_selection.py` | `31913f5915d804b2f2fbb127353863afcfa508fec65a9bebbdee708bdc81cb04` |
| `ml/scripts/select_observations.py` | `c9d84549378dc09485331d1aa13dd620502dcdb2700dba129401a2d8a3051aa4` |
| `ml/tests/test_explanations.py` | `08f343ac08261457a5bcdad7844ae9faffe10ce9e7ec617bd1eee00e39e0534d` |
| `ml/tests/test_weighting.py` | `9b07be93f7b0095828fe0b40fd9ffa0cdbebe30f5bdbd7b8c578fba74d94798b` |
| `ml/tests/test_windows.py` | `fc9bfc1a1decdce7fa75ab1f9a62efb487487fec1d28d817a4410ec7c51743ab` |
| `pytest.ini` | `93a935b81e09ef1609fd3974b79df15cec67d211d30e1afb23d203cf08c8d5d4` |
| `scripts/check_local_mqtt_chain.py` | `259834e090936b56544b8191955341e7ada3708a1f0c4ebf4671105ed5ab4761` |
| `scripts/select_additional_normal.py` | `a811eccdf3d57bbf85472538e3b6f32dbbe5bb5e9091636b3a1122312e5aeee6` |
| `scripts/summarize_phase_1_5_experiments.py` | `55e23e16c3a1f72704e2acc2d256c4b6222214fb27e6058fb37889cf326b0991` |
| `services/edge-agent/.dockerignore` | `f090888e234765c2f5493bdd35ba578215b2ce8530a8a2261dc99bae7494eecd` |
| `services/edge-agent/edge_agent/sequence.py` | `12d45fd872b1995697eff6a78f359cc452f6f1c789ba2756e1ee1823b517c538` |
