# 项目迁移基线

采集时间：2026-09-13T01:08:36+08:00（Asia/Shanghai）。本文件记录新增文档及提交之前的工作区快照，后续提交会改变 HEAD；基线 commit 不随之改写。

本阶段只新增本文件，不修改代码、配置、数据库、模型或部署，不运行训练与端到端测试，不删除历史实验。文档中的旧计划和历史验收要求仅作为证据，不替代用户最新迁移约束。

证据等级：**本轮核实**＝本次只读检查；**历史验收记录**＝已有报告，未重新执行；**尚未核实**＝缺少本轮实测，不推断已通过。文件修改时间不作为测试或部署发生时间。

## 1. 当前 Git 状态

- 分支：`codex/phase-1-5-completion`。
- 已跟踪修改：44 个文件。
- 未跟踪：53 个文件（按文件展开目录）。
- 暂存区：空。
- 本轮未 fetch/push，不把本地远端跟踪引用当成服务器最新状态。

## 2. 当前 commit

- 完整 SHA：`34e69ad8e680a41342d3168da6acc1098bb99496`。
- 说明：`fix: serve spa routes through web container`。
- 作者时间：`2026-09-12T20:31:29+08:00`。

- 本地引用 `main`：`34e69ad8e680a41342d3168da6acc1098bb99496`。
- 本地引用 `refs/remotes/origin/main`：`34e69ad8e680a41342d3168da6acc1098bb99496`。

这些引用只标识已提交内容，不包含以下工作区修改。

## 3. 既有未提交修改

以下清单共 97 个文件，全部在本文件创建前已存在。`M` 为已跟踪修改，`??` 为未跟踪；它们不属于本阶段新增，不进入本阶段提交。

### API

```text
M  apps/api/Dockerfile
M  apps/api/app/database.py
M  apps/api/app/diagnostics.py
M  apps/api/app/inference.py
M  apps/api/app/main.py
M  apps/api/app/models.py
M  apps/api/app/mqtt.py
M  apps/api/app/realtime.py
M  apps/api/app/schemas.py
M  apps/api/app/services.py
M  apps/api/requirements.txt
```

### 前端

```text
M  apps/web/Dockerfile
M  apps/web/src/App.vue
M  apps/web/src/api.ts
M  apps/web/src/router.ts
M  apps/web/src/views/AlarmsView.vue
M  apps/web/src/views/DiagnosticsView.vue
M  apps/web/src/views/EdgeView.vue
M  apps/web/src/views/MonitorView.vue
?? apps/web/.dockerignore
?? apps/web/src/views/HistoryView.vue
```

### 边缘代理

```text
M  services/edge-agent/docker-compose.yml
M  services/edge-agent/edge_agent/config.py
M  services/edge-agent/edge_agent/main.py
M  services/edge-agent/edge_agent/replay.py
?? services/edge-agent/.dockerignore
?? services/edge-agent/edge_agent/sequence.py
```

### ML

```text
M  ml/oilwell_ml/manifest.py
M  ml/oilwell_ml/split.py
M  ml/oilwell_ml/tcn_data.py
M  ml/requirements.txt
M  ml/scripts/generate_explanations.py
M  ml/scripts/prepare_demo_windows.py
M  ml/scripts/report_eda.py
M  ml/scripts/select_instances.py
M  ml/scripts/train_baselines.py
M  ml/scripts/train_tcn.py
?? ml/oilwell_ml/evaluation.py
?? ml/oilwell_ml/features_v2.py
?? ml/oilwell_ml/preprocessing.py
?? ml/oilwell_ml/weighting.py
?? ml/oilwell_ml/windows.py
?? ml/requirements-acceptance.lock.txt
?? ml/scripts/extend_training_selection.py
?? ml/scripts/select_observations.py
```

### 测试

```text
M  apps/api/tests/test_contract.py
M  apps/api/tests/test_diagnostics.py
M  apps/api/tests/test_inference.py
M  ml/tests/test_split.py
M  ml/tests/test_tcn_data.py
M  services/edge-agent/tests/test_replay.py
?? apps/api/tests/test_postgres_integration.py
?? apps/api/tests/test_realtime.py
?? ml/tests/test_explanations.py
?? ml/tests/test_weighting.py
?? ml/tests/test_windows.py
?? pytest.ini
```

### 文档

```text
M  docs/experiments/3w-eda-summary.json
M  docs/experiments/3w-instance-selection.json
M  docs/experiments/3w-manifest.json
M  docs/experiments/3w-split.json
?? docs/experiments/3w-expanded-manifest.json
?? docs/experiments/3w-observation-selection.json
?? docs/experiments/3w-supplement-manifest.json
?? docs/experiments/additional-data-request.md
?? docs/experiments/constant-signal-audit.json
?? docs/experiments/data-card.md
?? docs/experiments/domain-augmentation-protocol.md
?? docs/experiments/dynamics-protocol.md
?? docs/experiments/expanded-normal-training/decisions.json
?? docs/experiments/expanded-normal-training/selection.json
?? docs/experiments/expanded-normal-training/split.json
?? docs/experiments/expanded-training-protocol.md
?? docs/experiments/expanded-training/3w-eda-summary.json
?? docs/experiments/expanded-training/coverage.json
?? docs/experiments/expanded-training/decisions.json
?? docs/experiments/expanded-training/selection.json
?? docs/experiments/expanded-training/split.json
?? docs/experiments/interrupted-experiments.json
?? docs/experiments/normal-only-sources-protocol.md
?? docs/experiments/normal-segment-protocol.md
?? docs/experiments/phase-1-5-results.json
?? docs/experiments/relative-window-protocol.md
?? docs/experiments/runtime-environments.json
?? docs/experiments/supplement-coverage.json
?? docs/experiments/tcn-interleaving-protocol.md
?? docs/experiments/well-balanced-protocol.md
?? docs/experiments/window-shape-protocol.md
?? docs/experiments/zero-channel-protocol.md
?? docs/knowledge-base/retrieval-evaluation.json
?? docs/knowledge-base/review-packet.md
?? docs/knowledge-base/source-access-check.json
?? docs/phase-1-5-acceptance.md
```

### 根目录与工具脚本

```text
M  .dockerignore
?? scripts/check_local_mqtt_chain.py
?? scripts/select_additional_normal.py
?? scripts/summarize_phase_1_5_experiments.py
```

本次文档提交不会保护这些未提交文件。进入 Phase A 前，应单独提出检查点提交的文件范围、验证与回滚方案，经用户确认后再处理；不得使用整体 reset、clean 或覆盖式恢复。

## 4. 当前目录结构

本轮按实际存在目录整理；省略依赖缓存、Git 内部目录、私有数据的内部文件，不调整目录。
```text
oilwell-ai/
  apps/
    api/          # app、tests、Dockerfile、requirements
    web/          # src、Vue 页面、构建配置、Dockerfile
  services/
    edge-agent/   # edge_agent、tests、Dockerfile、Compose
  ml/
    oilwell_ml/   # 读取、窗口、特征、划分、训练支持
    scripts/      # 训练、数据审计、解释生成入口
    tests/
    data/         # 本地数据（忽略，不纳入提交）
    artifacts/    # 本地模型与实验制品（忽略）
  infra/          # Compose、MQTT 与部署配置
  scripts/        # 工程验证与实验汇总工具
  tests/
  docs/
    architecture/
    experiments/
    knowledge-base/
    .local/       # 忽略的本地验收证据
  README.md
  LICENSE
  pytest.ini
```

## 5. 已实现模块及能力边界

| 模块 | 源码证据 | 当前能力与限制 |
|---|---|---|
| 数据工程 | ml/oilwell_ml/、ml/scripts/ | 3W 读取、七变量、质量审计、按井划分、连续 180 点窗口与 10 点步长；数据充分性与跨井效果仍有局限。 |
| 边缘代理 | services/edge-agent/edge_agent/ | 回放、MQTT 遥测和心跳、命令处理、持久化 sequence；候选需 Pi 实机复验。 |
| 入库与服务 | apps/api/app/mqtt.py、services.py | MQTT/HTTP 遥测、去重、持久化、设备状态与推理结果。 |
| 推理 | apps/api/app/inference.py | 当前支持 XGBoost active 与 TCN shadow；XGBoost 服务仍按四分类契约计算 1-P(Normal)，并非正式二分类服务。 |
| 报警 | apps/api/app/services.py | active 结果驱动确认、恢复、再次触发和人工确认，shadow 不驱动报警。 |
| 实时与页面 | apps/api/app/realtime.py、apps/web/src/views/ | WebSocket、七变量曲线、历史查询、设备、模型、报警和诊断页面；包含本地回归后的未提交修复。 |
| 解释与诊断 | ml/scripts/generate_explanations.py、apps/api/app/diagnostics.py | 离线 SHAP、同窗口证据关联、知识检索和受控模板诊断；尚无真实外部 LLM 调用。 |

固定变量：`P_PDG`、`P_TPT`、`T_TPT`、`P_MON_CKP`、`T_JUS_CKP`、`P_JUS_CKGL`、`QGL`。源码存在与历史测试通过均不等于新方向整体验收完成。

## 6. 已完成测试与证据

本轮不重新运行测试、构建或回放脚本，不导入会创建运行时的 API 主模块，不连接或写入数据库。以下均为历史验收记录，本轮只核实证据文件存在和内容。

| 检查 | 历史结果 | 证据与边界 |
|---|---|---|
| 完整本地回归 | 74 项通过 | [验收登记](phase-1-5-acceptance.md) R01；涵盖 API、ML、Edge 和隔离 PostgreSQL，不是本轮复跑结果 |
| PostgreSQL | 去重、BIGINT/旧表迁移、报警恢复、shadow 隔离、诊断与历史查询 | 同上；生产数据库结构仍待实测 |
| 本地 MQTT 链路 | 命令回执、暂停/停止、序列号重启连续、入库与同窗口模型结果 | `.local/phase-1-5-completion/mqtt-chain.json`；隔离本地环境 |
| Broker 故障恢复 | 断线时命令 503，随后重连和命令确认 | `.local/phase-1-5-completion/mqtt-recovery.json` |
| 前端构建与浏览器 | 构建、七变量曲线、历史、诊断计时及重连有记录 | `.local/phase-1-5-completion/web-build-final.log`、`web-reconnect-build.log`、`browser-timings.json`、`monitor-reconnected.png` |
| 候选镜像 | API/Web amd64、Edge arm64 构建及 API 模型加载检查 | `.local/phase-1-5-completion/candidate-images.txt`、`api-image-inference-smoke.json`；本机模拟架构检查不等于 ECS 性能 |

验收登记中早期 57/63 项记录是中间状态，最新汇总为 74 项；本轮未发现独立最终 pytest 输出文件，74 项的证据等级保持为报告记载。旧四类模型门禁与旧“TCN 始终 shadow”要求已由用户新方向取代。

## 7. 当前部署状态

最近找到的正式演示证据日期为 **2026-09-12**：`.local/phase-5/acceptance-summary-20260912.md`。对应 release manifest 采集时间为 `2026-09-12T12:38:10.427460+00:00`。这是历史核验，不是本轮远程健康检查。

| 环境 | 最近历史证据 | 本轮结论 |
|---|---|---|
| Alibaba ECS | 历史 commit `34e69ad`；API health ok、MQTT 已连、active/shadow ready；模型、解释和知识库摘要与本地一致 | 未远程复核；当前在线版本、资源余量、数据库实际结构待核实 |
| Raspberry Pi | 2026-09-12 摘要记载 Edge Agent 运行、TLS MQTT 成功、回放自动启动关闭及四类数据回放记录 | 摘要没有 Pi 镜像 digest 或独立 commit；本轮不推断其当前版本，待核实 |
| 当前候选 | 补齐验收登记明确候选未部署、未合并；本地有构建结果 | 工作区最新代码不能声明已部署 |

- 历史 ECS `api` 镜像：`sha256:19c136ecf108d22e24c5f86e6a94585eeac60f78d0b23fbba0ffbe7a43e37078`。
- 历史 ECS `web` 镜像：`sha256:c5f8956ea9d4f7d99b79f31d77828e41554b36adb309260122108fbaed96996c`。
- 历史模型：`xgb-20260912T082447Z` active；`tcn-20260912T084752Z` shadow。
- 历史 Severe Slugging 回放中曾预测为 Normal，四类回放记录不能证明四类识别有效。

本地候选镜像（来自已有文件；不是本轮 Docker inspect，也不代表当前工作区全部变化已打入镜像）：
```text
[oilwell-ai-api:phase15-candidate] sha256:2016220243a0a969720d764da04673da43ae0459e99d4225eaebccf35f27dcf4 linux/amd64
[oilwell-ai-web:phase15-candidate] sha256:21276fb2ef65ad108ad61a3c4ff937e015b07f303a01663803050254ea9a0753 linux/amd64
[oilwell-ai-edge:phase15-candidate] sha256:c315ccfd22b9b5647d12cefb2ed74fc1c4828506477c43761a2c0a35412a371c linux/arm64
```

当前 Compose 声明 PostgreSQL 512 MiB、API 512 MiB、MQTT 128 MiB、Web 128 MiB 上限；上限合计不是实际内存占用。ECS 2C2G 还需考虑宿主与其他服务，本轮未采样。新生产边界仅允许默认 XGBoost 推理；当前双模型实现与制品挂载是迁移前事实，Phase B 才调整。

## 8. 已有模型制品

本轮仅读取元数据和计算文件 SHA-256，不加载 joblib/torch 模型，不训练，不复制制品。模型文件本体继续留在 Git 忽略目录；本地存在不等于部署或质量验收通过。

| 元数据路径 | 版本 | 类型 / schema | 窗口 / 步长 |
|---|---|---|---|
| `ml/artifacts/current/isolation_forest_metadata.json` | `if-20260912T082447Z` | isolation_forest / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/current/model_metadata.json` | `xgb-20260912T082447Z` | xgboost / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-augmented/current/isolation_forest_metadata.json` | `if-20260912T144331Z` | isolation_forest / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-augmented/current/model_metadata.json` | `xgb-20260912T144331Z` | xgboost / `3w-7v-window-relative-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-candidate/current/isolation_forest_metadata.json` | `if-20260912T141714Z` | isolation_forest / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-candidate/current/model_metadata.json` | `xgb-20260912T141714Z` | xgboost / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-candidate/tcn-shadow/model_metadata.json` | `tcn-20260912T142235Z` | tcn / `3w-7v-tcn-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-dynamics/current/isolation_forest_metadata.json` | `if-20260912T145525Z` | isolation_forest / `3w-7v-window-dynamics-v2` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-dynamics/current/model_metadata.json` | `xgb-20260912T145525Z` | xgboost / `3w-7v-window-dynamics-v2` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-expanded/current/isolation_forest_metadata.json` | `if-20260912T154850Z` | isolation_forest / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-expanded/current/model_metadata.json` | `xgb-20260912T154850Z` | xgboost / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-expanded-mps/tcn-shadow/model_metadata.json` | `tcn-20260912T161707Z` | tcn / `3w-7v-tcn-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-expanded-normal/current/isolation_forest_metadata.json` | `if-20260912T160235Z` | isolation_forest / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-expanded-normal/current/model_metadata.json` | `xgb-20260912T160235Z` | xgboost / `3w-7v-window-relative-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-interleaved/tcn-shadow/model_metadata.json` | `tcn-20260912T152229Z` | tcn / `3w-7v-tcn-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-normal-segments/current/isolation_forest_metadata.json` | `if-20260912T143313Z` | isolation_forest / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-normal-segments/current/model_metadata.json` | `xgb-20260912T143313Z` | xgboost / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-normal-segments/tcn-shadow/model_metadata.json` | `tcn-20260912T145724Z` | tcn / `3w-7v-tcn-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-relative/current/isolation_forest_metadata.json` | `if-20260912T142755Z` | isolation_forest / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-relative/current/model_metadata.json` | `xgb-20260912T142755Z` | xgboost / `3w-7v-window-relative-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-shape/current/isolation_forest_metadata.json` | `if-20260912T151729Z` | isolation_forest / `3w-7v-window-dynamics-v2` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-shape/current/model_metadata.json` | `xgb-20260912T151729Z` | xgboost / `3w-7v-window-dynamics-v2` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-well-balanced/current/isolation_forest_metadata.json` | `if-20260912T161218Z` | isolation_forest / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-well-balanced/current/model_metadata.json` | `xgb-20260912T161218Z` | xgboost / `3w-7v-window-relative-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-zero-channel/current/isolation_forest_metadata.json` | `if-20260912T162155Z` | isolation_forest / `3w-7v-window-stats-v1` | 180 / 10 秒 |
| `ml/artifacts/phase-1-5-zero-channel/current/model_metadata.json` | `xgb-20260912T162155Z` | xgboost / `3w-7v-window-relative-v1` | 180 / 10 秒 |
| `ml/artifacts/tcn-shadow/model_metadata.json` | `tcn-20260912T084752Z` | tcn / `3w-7v-tcn-v1` | 180 / 10 秒 |

`current/` 含四分类 XGBoost、二分类 `xgboost_binary.json`、Isolation Forest；二分类文件存在不代表具有独立且完整的服务元数据。`tcn-shadow/` 含权重、配置及 scaler。历史四分类失败实验全部保留，新方向冻结其继续优化；IF 仅 baseline，TCN 仅离线实验。

实验目录（本轮实际存在）：

- `ml/artifacts/phase-1-5-augmented/`
- `ml/artifacts/phase-1-5-candidate/`
- `ml/artifacts/phase-1-5-dynamics/`
- `ml/artifacts/phase-1-5-expanded/`
- `ml/artifacts/phase-1-5-expanded-mps/`
- `ml/artifacts/phase-1-5-expanded-normal/`
- `ml/artifacts/phase-1-5-interleaved/`
- `ml/artifacts/phase-1-5-normal-segments/`
- `ml/artifacts/phase-1-5-relative/`
- `ml/artifacts/phase-1-5-shape/`
- `ml/artifacts/phase-1-5-well-balanced/`
- `ml/artifacts/phase-1-5-zero-channel/`

[历史实验汇总](experiments/phase-1-5-results.json)记载 14 个完整模型实验；实验数量与顶层目录数量并非一一对应。

### 制品文件 SHA-256

以下覆盖模型权重、模型元数据、配置、scaler、指标和对照报告；不把原始数据或训练缓存纳入制品清单。

| 路径 | 字节数 | SHA-256 |
|---|---:|---|
| `ml/artifacts/current/isolation_forest.joblib` | 1355021 | `7322f311c0f91821b7f302dc293995d94f6e44b2a3e598986c8be03a2ee2db3c` |
| `ml/artifacts/current/isolation_forest_metadata.json` | 3300 | `b134ee1a02075c69294ccfe2ff24ce78ee206c8c5b5407db79e3b6abc6408b78` |
| `ml/artifacts/current/metrics.json` | 3836 | `16b62b73893150b219c73a9f412be7d2d335cee9757c72e8c2d6927494f8ccbb` |
| `ml/artifacts/current/model_metadata.json` | 4837 | `d8451cf246c95130ec4b43057a26480f54415aec3e24c8a9d1b3ce22fb091b4c` |
| `ml/artifacts/current/xgboost_binary.json` | 121672 | `c972d0d318f1b020ad4300b59998f03ddab3b395a434c41a74b4d7b664ae09e2` |
| `ml/artifacts/current/xgboost_model.json` | 712938 | `5ffa7134bbf0b1b5e639aad69173f3898f36131f481bbe1623da6a260a29c606` |
| `ml/artifacts/phase-1-5-augmented/current/isolation_forest.joblib` | 1293949 | `681ca4993f05e160b7310fcfb60866ace438ae5ce3f3e7dfa5f8ab05314cec61` |
| `ml/artifacts/phase-1-5-augmented/current/isolation_forest_metadata.json` | 3935 | `96b921206081558f9b1a3d623833b2766d74bd85386833f6ebd5f7616b18a64b` |
| `ml/artifacts/phase-1-5-augmented/current/metrics.json` | 8544 | `2326ab73d4dd0f3da86dc0dff4d1f15b8bfa8e38520b7c505d68322eb3e5f59f` |
| `ml/artifacts/phase-1-5-augmented/current/model_metadata.json` | 23030 | `f4dadf504f85569a6a802e4c03ce1a119104799c1394f471b8afa234c42b9ce8` |
| `ml/artifacts/phase-1-5-augmented/current/xgboost_binary.json` | 955206 | `b7ecf25f393efcbf3f4690c1ef1d7e069768bc15a437316cdd8c242bd8308d5b` |
| `ml/artifacts/phase-1-5-augmented/current/xgboost_model.json` | 1159403 | `374b3557fcb2da149f828d792128514f1bf0761925a6f645dde53ba8c9b9778e` |
| `ml/artifacts/phase-1-5-candidate/current/isolation_forest.joblib` | 1471533 | `be0a501ca984427e275af80a753aa15cdd2ae6ce5ccb2f732cce16cb0f8c4dae` |
| `ml/artifacts/phase-1-5-candidate/current/isolation_forest_metadata.json` | 3934 | `bb1500c7e350aedb2f0d2f66c779ca50933db4a5f49dc3a3a468a8918d0969db` |
| `ml/artifacts/phase-1-5-candidate/current/metrics.json` | 8030 | `614a4176207e69f413aeca655f46671285274c795a6c56258665f364c33003c8` |
| `ml/artifacts/phase-1-5-candidate/current/model_metadata.json` | 15437 | `6faee7025478dca0006a1da02c3086f9c91efa8fd4fec3e5007d75eb4fe301e1` |
| `ml/artifacts/phase-1-5-candidate/current/xgboost_binary.json` | 157028 | `042e7853aac2232c68e3eafc47e4834efa37713ffc3d4c7bebc146090276225c` |
| `ml/artifacts/phase-1-5-candidate/current/xgboost_model.json` | 626687 | `6acda4d3392a0537bbfb8a1f48909563fc92894b94c8d5d3680dec908952adce` |
| `ml/artifacts/phase-1-5-candidate/tcn-shadow/comparison.json` | 6092 | `1203d0d8228573a4b6b2dab3b9045885b83910571b9cbe30a2e8104497fc9a60` |
| `ml/artifacts/phase-1-5-candidate/tcn-shadow/model_metadata.json` | 17391 | `216ef0f29fd59c2cb2ca584ecb35e04d1271e510ffa0595eb863fe2d367c632e` |
| `ml/artifacts/phase-1-5-candidate/tcn-shadow/scaler.json` | 491 | `9a83243112e798a184669f63dcbb80cbf7e81ba4df453e5b86b80f7456b1769f` |
| `ml/artifacts/phase-1-5-candidate/tcn-shadow/tcn_config.json` | 148 | `d96d90a6c1ed4af4598955ef819ac88501b2eda5a050426028cd849f510cc7f0` |
| `ml/artifacts/phase-1-5-candidate/tcn-shadow/tcn_model.pt` | 205533 | `71753742cfd65e49222fdb872b1ec5d7a3cdd93b83f2a6087a71bd9baa0d45f8` |
| `ml/artifacts/phase-1-5-dynamics/current/isolation_forest.joblib` | 1177885 | `9ed77bff3b7f70712331aa0858ece84ac740f8ac8fb5202826e9232d798abf83` |
| `ml/artifacts/phase-1-5-dynamics/current/isolation_forest_metadata.json` | 5641 | `25abc1a919d19a4b9034ae5b180743450facd28d901fb7389fc9085f59cb3ed9` |
| `ml/artifacts/phase-1-5-dynamics/current/metrics.json` | 8551 | `203f3cd9a8e0a145d30ad936682490bc022fa4512625f24a4e2b38135ba51a59` |
| `ml/artifacts/phase-1-5-dynamics/current/model_metadata.json` | 24150 | `8a5e83dbafdbce259deca00335b693405e486f249eb2b68a296587720be3aec1` |
| `ml/artifacts/phase-1-5-dynamics/current/xgboost_binary.json` | 269647 | `8f47b85f644fc81cd9296185d04696e3ef4d7c3090e9f266c42e035bf539442d` |
| `ml/artifacts/phase-1-5-dynamics/current/xgboost_model.json` | 785982 | `cebb6dddb4bb79814a0a48cb5e9ade9b8cda7e59478442322f5b71089e19bd35` |
| `ml/artifacts/phase-1-5-expanded/current/isolation_forest.joblib` | 1053709 | `085a4eca4c03e17266b5a37fedeaeac7aa0502492b083ea1e1a76067d448edb2` |
| `ml/artifacts/phase-1-5-expanded/current/isolation_forest_metadata.json` | 4012 | `e568c224f3f869eee7b94fbe026ae8e0b3f784320b6d9ca016c6cabd42372ab8` |
| `ml/artifacts/phase-1-5-expanded/current/metrics.json` | 8459 | `44cbca88bebe75aafc6a77d9097cdf5993354c4efeadecd2e9b4c4ac616fca53` |
| `ml/artifacts/phase-1-5-expanded/current/model_metadata.json` | 22314 | `94974aea69807e24202d73a166ace644abc5d020770f32037e33ce06996fd97c` |
| `ml/artifacts/phase-1-5-expanded/current/xgboost_binary.json` | 621495 | `c55c3299ffa9f49e1b9fe46529fc8d0a10089611d975a924c90c66414abf8c65` |
| `ml/artifacts/phase-1-5-expanded/current/xgboost_model.json` | 1091469 | `7dabd5ebdcff7d4c211d141533ac0de385cc2cfb9c30c045d6bc3ce4f9821500` |
| `ml/artifacts/phase-1-5-expanded-mps/tcn-shadow/comparison.json` | 6454 | `235f7dcb4821a4b1e75da89f7640de519eacf8f042cddf8a55a701a3881c9cd5` |
| `ml/artifacts/phase-1-5-expanded-mps/tcn-shadow/model_metadata.json` | 19926 | `ec58777419c7af35a2b7231f168eeb409f25ff84f1497d46435823ff6d2e22e2` |
| `ml/artifacts/phase-1-5-expanded-mps/tcn-shadow/scaler.json` | 486 | `bbe474a9f53818862bcab3010591fb6091ffaeefda219bab47c8006973674cf7` |
| `ml/artifacts/phase-1-5-expanded-mps/tcn-shadow/tcn_config.json` | 148 | `d96d90a6c1ed4af4598955ef819ac88501b2eda5a050426028cd849f510cc7f0` |
| `ml/artifacts/phase-1-5-expanded-mps/tcn-shadow/tcn_model.pt` | 205533 | `664974ba07b0bce4e8c295aa84ba42940ec061e2134a496d8f4aa35b2c881ef7` |
| `ml/artifacts/phase-1-5-expanded-normal/current/isolation_forest.joblib` | 965181 | `56e07d8c50ebdca8e3307387e9fed7f086b67b072745acbc1177694858449d12` |
| `ml/artifacts/phase-1-5-expanded-normal/current/isolation_forest_metadata.json` | 4057 | `0034c7dae30d0bd717ef3bd559d0ffc606fd87030018d08aae04f2fa9d65acb4` |
| `ml/artifacts/phase-1-5-expanded-normal/current/metrics.json` | 8545 | `f5c926bc455637fae3a078265e5c8b544162782a9606089511367c67512a5963` |
| `ml/artifacts/phase-1-5-expanded-normal/current/model_metadata.json` | 22280 | `b8cc3f3e935d6a5db86475bd81711bc5c8dcf773e3d78bd6303b66419fb4afb3` |
| `ml/artifacts/phase-1-5-expanded-normal/current/xgboost_binary.json` | 610583 | `0cbcd9112b539d8a9392b15681da9f9992a27c1078e4a21f7841813ad90bb871` |
| `ml/artifacts/phase-1-5-expanded-normal/current/xgboost_model.json` | 1164842 | `26073704d6ce599423e86660dfbcbfbab97b3ecf61bbe922bf34fc71dc4b7799` |
| `ml/artifacts/phase-1-5-interleaved/tcn-shadow/comparison.json` | 6488 | `6acbb5f2b9acd0230033c2e9ad1253ce00d656613807ad50422824bc48d52f42` |
| `ml/artifacts/phase-1-5-interleaved/tcn-shadow/model_metadata.json` | 28544 | `83cd5d0c3be66f48f7bc20e99a914e4ae48334d3e40174d86b053354708ba031` |
| `ml/artifacts/phase-1-5-interleaved/tcn-shadow/scaler.json` | 488 | `0498bcc162e6a1ab2a24f6bfeeedb1253775e8a87ed757e4544ed56d9010c0de` |
| `ml/artifacts/phase-1-5-interleaved/tcn-shadow/tcn_config.json` | 148 | `d96d90a6c1ed4af4598955ef819ac88501b2eda5a050426028cd849f510cc7f0` |
| `ml/artifacts/phase-1-5-interleaved/tcn-shadow/tcn_model.pt` | 205533 | `a22fc95b5f5a02cce9b030fcad68a2cb5d6ae51f3c9227540eeb87351507ef00` |
| `ml/artifacts/phase-1-5-normal-segments/current/isolation_forest.joblib` | 1293949 | `681ca4993f05e160b7310fcfb60866ace438ae5ce3f3e7dfa5f8ab05314cec61` |
| `ml/artifacts/phase-1-5-normal-segments/current/isolation_forest_metadata.json` | 3934 | `d080aa466548a1373b5644f5a67261979510e6d9ce15f41740f47a961887e5df` |
| `ml/artifacts/phase-1-5-normal-segments/current/metrics.json` | 8474 | `af16ad603c96f4d77b395c58d0eb8d6abb613529a61cea42a1c3d8b7ed9289f8` |
| `ml/artifacts/phase-1-5-normal-segments/current/model_metadata.json` | 22520 | `862a0889048a24fb39fb4c7dd1f4881bc0d86f8bb18d5582f0d7d4b234c8fb24` |
| `ml/artifacts/phase-1-5-normal-segments/current/xgboost_binary.json` | 269331 | `44bd19c6ec8e9662b8e72b8870f674ce5e43355b5c4c00472837ec82033aaba4` |
| `ml/artifacts/phase-1-5-normal-segments/current/xgboost_model.json` | 788386 | `610775ff278db93cac7ac9bb919048548d3b826d312a6e9f949b8b2534aa357b` |
| `ml/artifacts/phase-1-5-normal-segments/tcn-shadow/comparison.json` | 6412 | `1b0fb06bac12f491084f193322d0e28fdae0460fd2896b64f0e4945157434b02` |
| `ml/artifacts/phase-1-5-normal-segments/tcn-shadow/model_metadata.json` | 21332 | `c5469f68e9b65d09f036a58baeab122fd4ef64e0b4a13ff01a70f224cb63a27b` |
| `ml/artifacts/phase-1-5-normal-segments/tcn-shadow/scaler.json` | 488 | `0498bcc162e6a1ab2a24f6bfeeedb1253775e8a87ed757e4544ed56d9010c0de` |
| `ml/artifacts/phase-1-5-normal-segments/tcn-shadow/tcn_config.json` | 148 | `d96d90a6c1ed4af4598955ef819ac88501b2eda5a050426028cd849f510cc7f0` |
| `ml/artifacts/phase-1-5-normal-segments/tcn-shadow/tcn_model.pt` | 205533 | `ef7a9ac93c075d982f9cdfd3b9fb2020b0d4fd5346b434c2d21394b09ffe62d5` |
| `ml/artifacts/phase-1-5-relative/current/isolation_forest.joblib` | 1471533 | `be0a501ca984427e275af80a753aa15cdd2ae6ce5ccb2f732cce16cb0f8c4dae` |
| `ml/artifacts/phase-1-5-relative/current/isolation_forest_metadata.json` | 3935 | `ac8780e6239559f4f8805c623496561e0a9646a2a0f69a8a31c993f6bbeadc5d` |
| `ml/artifacts/phase-1-5-relative/current/metrics.json` | 8143 | `101a208766c60f0f3f59a6a526cedd9b8bcdf65ca4b9532904974c5e2ce79de2` |
| `ml/artifacts/phase-1-5-relative/current/model_metadata.json` | 22138 | `e085b1db9a2536ffb2319cb2eb86efea39756edb55d49054e1d429dcc02b24fc` |
| `ml/artifacts/phase-1-5-relative/current/xgboost_binary.json` | 157028 | `042e7853aac2232c68e3eafc47e4834efa37713ffc3d4c7bebc146090276225c` |
| `ml/artifacts/phase-1-5-relative/current/xgboost_model.json` | 842822 | `3a1c0c4bb934621273e68f1905cebd1e745c9be05db3712f31ea7ccd0209a925` |
| `ml/artifacts/phase-1-5-shape/current/isolation_forest.joblib` | 1177885 | `9ed77bff3b7f70712331aa0858ece84ac740f8ac8fb5202826e9232d798abf83` |
| `ml/artifacts/phase-1-5-shape/current/isolation_forest_metadata.json` | 5640 | `df4117bc1febef8d503bcb10156296155c2b16584a427daa39a1db81d9647492` |
| `ml/artifacts/phase-1-5-shape/current/metrics.json` | 8710 | `bda95e9f4aa8bdafd2aae92507b10c8e7fd5b07e198fba64c0f7546c28edb013` |
| `ml/artifacts/phase-1-5-shape/current/model_metadata.json` | 18152 | `90962812d65bd93461e22ea0a5137ffb7d90080be90de44869c175178df3ba34` |
| `ml/artifacts/phase-1-5-shape/current/xgboost_binary.json` | 269647 | `8f47b85f644fc81cd9296185d04696e3ef4d7c3090e9f266c42e035bf539442d` |
| `ml/artifacts/phase-1-5-shape/current/xgboost_model.json` | 3388459 | `3f521ac7c739b55c58b844477aec863af47968ae249cbad1e35a1d9ed90cdcb3` |
| `ml/artifacts/phase-1-5-well-balanced/current/isolation_forest.joblib` | 965181 | `56e07d8c50ebdca8e3307387e9fed7f086b67b072745acbc1177694858449d12` |
| `ml/artifacts/phase-1-5-well-balanced/current/isolation_forest_metadata.json` | 4057 | `fcebd7a3c0f7e161ca2643500396ed86912dd30d2b76aeac33df2086a03a8e4d` |
| `ml/artifacts/phase-1-5-well-balanced/current/metrics.json` | 8578 | `0dfa2ed617bb031f1ed0bf91e97a7230818ba50bdff690e4a211df448dedbf44` |
| `ml/artifacts/phase-1-5-well-balanced/current/model_metadata.json` | 22343 | `b8d1d8b820bff12198c3f37a1ae729988fc8bb0cd6e51f13db3d1291c995b364` |
| `ml/artifacts/phase-1-5-well-balanced/current/xgboost_binary.json` | 845179 | `e68a64e63d6f2a24d50398093c5a400ae03d8f2b1a720618cff5f2eda31a5d52` |
| `ml/artifacts/phase-1-5-well-balanced/current/xgboost_model.json` | 1158566 | `646d71680f65fb0546745e767b7b1a42b5db00ae63c71eb34c40ecf886feb5ad` |
| `ml/artifacts/phase-1-5-zero-channel/current/isolation_forest.joblib` | 965181 | `56e07d8c50ebdca8e3307387e9fed7f086b67b072745acbc1177694858449d12` |
| `ml/artifacts/phase-1-5-zero-channel/current/isolation_forest_metadata.json` | 4057 | `735ea6a1a452dc809d4b9d7cf1cf2972b7c6a104707642e10a5b1a1c1bed5aab` |
| `ml/artifacts/phase-1-5-zero-channel/current/metrics.json` | 8532 | `aa5744c289912159f077192bf1fc448d344e482d2d8c2d3c5b183fa36098ae4f` |
| `ml/artifacts/phase-1-5-zero-channel/current/model_metadata.json` | 23219 | `7b20c04ac0b2e84f73a2765ffc0e4e917c854a285c3c36d73de04f13c47e3db1` |
| `ml/artifacts/phase-1-5-zero-channel/current/xgboost_binary.json` | 653864 | `6fc39158bd3ec32d8d73e6720b3f5ec8b8d4f675cb39a3ab8a42ddc22e1498e1` |
| `ml/artifacts/phase-1-5-zero-channel/current/xgboost_model.json` | 10285511 | `00559f3fd7deb53890abd5a0625ebfde44e65e9ff8925065b1dc1ae662a9ed89` |
| `ml/artifacts/tcn-shadow/comparison.json` | 3567 | `6765ac508fddc74dffe12e943c617650000a678db756d792e0e2a039b6828b50` |
| `ml/artifacts/tcn-shadow/model_metadata.json` | 2869 | `bebc2ecf58a57a33cc8f44c675abd21f73d6959f14d0589e6730460b8f7cda51` |
| `ml/artifacts/tcn-shadow/scaler.json` | 486 | `d4867f7f7e53fc0430c5b54f0a4503e6669a07c0dcac589fb08ac2afac67b8ff` |
| `ml/artifacts/tcn-shadow/tcn_config.json` | 148 | `d96d90a6c1ed4af4598955ef819ac88501b2eda5a050426028cd849f510cc7f0` |
| `ml/artifacts/tcn-shadow/tcn_model.pt` | 205533 | `21ce43c87bc9bb96dac5d99daf66f2ba2d5b28b84ad24d721b5870555b4a00ee` |

## 9. 当前数据库结构

**本轮核实的是 SQLAlchemy 源码定义，不是数据库实测。** 未执行 DDL、迁移、查询或启动应用。类型/可空性来自 `Mapped` 注解及 `mapped_column`；包含 `None` 的非主键字段可空，其余字段非空。`default` 为 ORM 侧默认，`server_default` 为数据库默认。

### `wells`

| ORM 字段 | Python 注解 | 列定义（含类型、外键、索引与默认值） |
|---|---|---|
| `id` | `Mapped[str]` | `mapped_column(String(64), primary_key=True)` |
| `display_name` | `Mapped[str &#124; None]` | `mapped_column(String(120))` |
| `created_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), server_default=func.now())` |

### `edge_devices`

| ORM 字段 | Python 注解 | 列定义（含类型、外键、索引与默认值） |
|---|---|---|
| `id` | `Mapped[str]` | `mapped_column(String(64), primary_key=True)` |
| `status` | `Mapped[str]` | `mapped_column(String(24), default='OFFLINE')` |
| `last_heartbeat` | `Mapped[datetime &#124; None]` | `mapped_column(DateTime(timezone=True))` |
| `metadata_` | `Mapped[dict]` | `mapped_column('metadata', JSONB, default=dict)` |

### `telemetry`

| ORM 字段 | Python 注解 | 列定义（含类型、外键、索引与默认值） |
|---|---|---|
| `id` | `Mapped[int]` | `mapped_column(Integer, primary_key=True)` |
| `device_id` | `Mapped[str]` | `mapped_column(ForeignKey('edge_devices.id'), index=True)` |
| `well_id` | `Mapped[str]` | `mapped_column(ForeignKey('wells.id'), index=True)` |
| `timestamp` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), index=True)` |
| `sequence` | `Mapped[int]` | `mapped_column(BigInteger)` |
| `p_pdg` | `Mapped[float]` | `mapped_column(Float)` |
| `p_tpt` | `Mapped[float]` | `mapped_column(Float)` |
| `t_tpt` | `Mapped[float]` | `mapped_column(Float)` |
| `p_mon_ckp` | `Mapped[float]` | `mapped_column(Float)` |
| `t_jus_ckp` | `Mapped[float]` | `mapped_column(Float)` |
| `p_jus_ckgl` | `Mapped[float]` | `mapped_column(Float)` |
| `qgl` | `Mapped[float]` | `mapped_column(Float)` |
| `event_hint` | `Mapped[str &#124; None]` | `mapped_column(String(80))` |
| `extras` | `Mapped[dict]` | `mapped_column(JSONB, default=dict)` |

表级约束：`(UniqueConstraint('device_id', 'sequence', name='uq_telemetry_device_sequence'),)`。

### `alarms`

| ORM 字段 | Python 注解 | 列定义（含类型、外键、索引与默认值） |
|---|---|---|
| `id` | `Mapped[int]` | `mapped_column(Integer, primary_key=True)` |
| `well_id` | `Mapped[str]` | `mapped_column(ForeignKey('wells.id'), index=True)` |
| `telemetry_id` | `Mapped[int &#124; None]` | `mapped_column(ForeignKey('telemetry.id'))` |
| `severity` | `Mapped[str]` | `mapped_column(String(16))` |
| `event_type` | `Mapped[str]` | `mapped_column(String(80))` |
| `status` | `Mapped[str]` | `mapped_column(String(24), default='UNACKNOWLEDGED', index=True)` |
| `message` | `Mapped[str]` | `mapped_column(Text)` |
| `raised_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), server_default=func.now())` |
| `acknowledged_at` | `Mapped[datetime &#124; None]` | `mapped_column(DateTime(timezone=True))` |
| `resolved_at` | `Mapped[datetime &#124; None]` | `mapped_column(DateTime(timezone=True))` |

### `alarm_states`

| ORM 字段 | Python 注解 | 列定义（含类型、外键、索引与默认值） |
|---|---|---|
| `well_id` | `Mapped[str]` | `mapped_column(ForeignKey('wells.id'), primary_key=True)` |
| `abnormal_streak` | `Mapped[int]` | `mapped_column(Integer, default=0)` |
| `normal_streak` | `Mapped[int]` | `mapped_column(Integer, default=0)` |
| `armed` | `Mapped[bool]` | `mapped_column(default=True)` |
| `active_alarm_id` | `Mapped[int &#124; None]` | `mapped_column(ForeignKey('alarms.id'))` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())` |

### `inference_results`

| ORM 字段 | Python 注解 | 列定义（含类型、外键、索引与默认值） |
|---|---|---|
| `id` | `Mapped[int]` | `mapped_column(Integer, primary_key=True)` |
| `well_id` | `Mapped[str]` | `mapped_column(ForeignKey('wells.id'), index=True)` |
| `telemetry_id` | `Mapped[int]` | `mapped_column(ForeignKey('telemetry.id'), index=True)` |
| `model_type` | `Mapped[str]` | `mapped_column(String(32), index=True)` |
| `model_mode` | `Mapped[str]` | `mapped_column(String(16), index=True)` |
| `status` | `Mapped[str]` | `mapped_column(String(32), index=True)` |
| `window_start` | `Mapped[datetime &#124; None]` | `mapped_column(DateTime(timezone=True))` |
| `window_end` | `Mapped[datetime &#124; None]` | `mapped_column(DateTime(timezone=True))` |
| `model_version` | `Mapped[str &#124; None]` | `mapped_column(String(80), index=True)` |
| `predicted_class` | `Mapped[str &#124; None]` | `mapped_column(String(80))` |
| `confidence` | `Mapped[float &#124; None]` | `mapped_column(Float)` |
| `anomaly_score` | `Mapped[float &#124; None]` | `mapped_column(Float)` |
| `feature_schema_version` | `Mapped[str &#124; None]` | `mapped_column(String(80))` |
| `inference_latency_ms` | `Mapped[float &#124; None]` | `mapped_column(Float)` |
| `created_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), server_default=func.now())` |

表级约束：`(UniqueConstraint('telemetry_id', 'model_mode', name='uq_inference_telemetry_model_mode'),)`。

### `diagnostic_records`

| ORM 字段 | Python 注解 | 列定义（含类型、外键、索引与默认值） |
|---|---|---|
| `id` | `Mapped[int]` | `mapped_column(Integer, primary_key=True)` |
| `well_id` | `Mapped[str]` | `mapped_column(ForeignKey('wells.id'), index=True)` |
| `inference_id` | `Mapped[int]` | `mapped_column(ForeignKey('inference_results.id'), index=True)` |
| `request_id` | `Mapped[str]` | `mapped_column(String(36), unique=True, index=True)` |
| `status` | `Mapped[str]` | `mapped_column(String(32), index=True)` |
| `model_version` | `Mapped[str &#124; None]` | `mapped_column(String(80))` |
| `knowledge_base_version` | `Mapped[str]` | `mapped_column(String(80))` |
| `explanation_version` | `Mapped[str &#124; None]` | `mapped_column(String(80))` |
| `content` | `Mapped[str]` | `mapped_column(Text)` |
| `citations` | `Mapped[list]` | `mapped_column(JSONB, default=list)` |
| `input_summary` | `Mapped[dict]` | `mapped_column(JSONB, default=dict)` |
| `evidence_status` | `Mapped[str]` | `mapped_column(String(16), default='complete', index=True)` |
| `degradation_reasons` | `Mapped[list]` | `mapped_column(JSONB, default=list)` |
| `created_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), server_default=func.now())` |

`edge_devices.metadata_` 对应数据库列名 `metadata`。各 `index=True` 字段声明索引；`diagnostic_records.request_id` 声明唯一索引。外键、约束与索引是否已存在于生产实例，均待只读 schema 核验。

### 启动时迁移

`main.py` lifespan 先执行 `Base.metadata.create_all`，再执行 `database.py:migrate_schema`。PostgreSQL 分支包含：

1. 为 `alarms` 增加可空 `resolved_at TIMESTAMPTZ`。
2. 若 `telemetry.sequence` 为 integer，则升级为 BIGINT。
3. 删除旧 `uq_inference_telemetry`；为推理表补充 `model_type`（默认 xgboost）、`model_mode`（默认 active）。
4. 删除后重建 `(telemetry_id, model_mode)` 唯一约束。
5. 为诊断表增加 `evidence_status`（默认 complete）和 `degradation_reasons`（默认空 JSONB 数组）。

这些是源码中的启动行为，不表示本次已经执行。主键、表级约束与迁移行为在代码回滚时需另行评估；本次文档回滚不涉及数据库。

## 10. 当前 API 列表

本轮静态读取 `apps/api/app/main.py`，共 16 个显式 HTTP 路由和 1 个 WebSocket；不包括 FastAPI 默认文档/OpenAPI 路由。不是在线端点探测。

| 方法 | 路径 | 用途 / 主要约束 |
|---|---|---|
| GET | `/api/health` | 健康、MQTT 连接及模型状态 |
| POST | `/api/telemetry` | TelemetryIn 入库、去重、窗口推理及广播；202 |
| POST | `/api/edge-devices/status` | DeviceStatusIn 心跳/设备状态；202 |
| GET | `/api/dashboard` | 井数、在线设备数、未确认报警数 |
| GET | `/api/wells` | 井列表 |
| GET | `/api/wells/{well_id}/telemetry` | 遥测历史；limit 1–5000，start/end |
| GET | `/api/wells/{well_id}/inference` | 推理历史；mode、时间、event_class、limit 1–5000 |
| GET | `/api/wells/{well_id}/inference/latest` | 最新 active/shadow 结果；默认 active |
| GET | `/api/models` | 运行时模型状态 |
| GET | `/api/wells/{well_id}/inference/comparison/latest` | 最新同遥测点模型对照 |
| POST | `/api/wells/{well_id}/diagnostics` | 以 inference_id 创建持久化诊断；201 |
| GET | `/api/wells/{well_id}/diagnostics` | 诊断历史；limit 1–100 |
| GET | `/api/alarms` | 最近最多 200 条报警，可按 status 筛选 |
| POST | `/api/alarms/{alarm_id}/acknowledge` | 人工确认报警并广播 |
| GET | `/api/edge-devices` | 设备与心跳；超过 30 秒标记离线 |
| POST | `/api/replay/{device_id}/commands` | START/STOP/PAUSE/SET_SPEED/LOAD_INSTANCE 命令入队及 command_id；202，断线 503 |
| WEBSOCKET | `/ws` | 实时 telemetry、inference、alarm、device_status 等事件 |

当前没有 `POST /api/inference`；本阶段不新增。诊断使用已有持久化推理结果，当前是受控检索与模板，不是 LLM API 服务。遥测字段为七变量、well_id、device_id、timestamp、sequence 等；不把数据样本或凭据写入本文件。

## 11. 后续约束、提交与回滚

- 当前只完成文档基线。每个后续小阶段先说明修改文件、原因、验证和回滚，经用户确认后执行，通过验证后单独 commit。
- Phase A：验证 Pi → MQTT → FastAPI → PostgreSQL → inference → alarm → WebSocket → Vue，保持系统可运行，仅针对实证问题修复。
- Phase B：二分类服务迁移，生产默认仅 XGBoost；IF 仅 baseline，TCN 仅离线；不新增模型、不大规模调参。
- Phase C：SHAP 缓存、七变量贡献映射、报警解释页面。
- Phase D：前三阶段完成后才开发 RAG/LLM，使用外部 API。
- 不大规模重构，不删除实验，不无故修改已验证功能；ECS 2C2G 默认不部署本地 LLM、大型向量数据库或多模型在线推理。
- 首页与验收重点为 anomaly score、alarm latency、false alarm rate、recall、detection delay；事件分类及 Accuracy 不作为系统门禁。
- 提交仅暂存本文件，消息 `docs: record migration baseline`；不夹带已有工作区修改，不推送、不合并。
- 回滚仅撤销本次文档提交；不整体重置工作区，不回滚服务或数据库。

### 本文证据与复核边界

相对链接指向仓库文件；`.local/`、模型制品以及部分未跟踪报告未包含在本次文档提交中。仅克隆本次提交无法还原所有证据与既有工作区修改；Phase A 前的检查点方案需要解决这一限制。

| 证据文件 | 本轮 SHA-256 |
|---|---|
| `apps/api/app/models.py` | `bcd2bdf722fd09515dee5d5ed77e7463e950c743c6c7591627cd3112d65626b6` |
| `apps/api/app/database.py` | `598bcff5506d73d6a2f0a39335937c68f9d0a1b57250f5a28a7149e10086e203` |
| `apps/api/app/main.py` | `fc4261eba7565ec05dd2cb70f186828f38f821b15b73cda58654431e9fceb4fc` |
| `docs/phase-1-5-acceptance.md` | `fa9b10c66b6557dc9f048866e661c7e944f3e611578abbeac2bbde7c0254a0b8` |
| `docs/experiments/phase-1-5-results.json` | `4ef1f09598ff519a8c79a1003806171a11c690bf2b3525ab1c7c7614ccdb5e61` |
| `docs/.local/phase-5/acceptance-summary-20260912.md` | `22f3951d3977514a49746cda846072d39035ab99a9fd9443ef04035136c66df9` |
| `docs/.local/phase-5/release/manifest.json` | `2585f2f2758ed03c3181771ada0153c650d79c197f4f794b068fc2bb9172439b` |
| `docs/.local/phase-1-5-completion/mqtt-chain.json` | `9db406ba6ec07fc56a3cff797e6f91cfb23a4186ac6c438e357f64430738c989` |
| `docs/.local/phase-1-5-completion/mqtt-recovery.json` | `5b81e92c56e1bb52e141fd979032ececc337910f61565cbc7ea4cb12b1cca32e` |
| `docs/.local/phase-1-5-completion/candidate-images.txt` | `338f572d653b60d8cbc92b610330b88e6c3ca695393756f3093319f57a64bc77` |
