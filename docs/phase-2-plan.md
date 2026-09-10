# 第二步实施计划：3W 数据工程与可部署的 AI 基线

## 目标与边界

本阶段在已经完成的边云通信、数据接收、可视化和基础部署之上，交付可复现的 **3W 数据处理 + Isolation Forest + XGBoost 推理闭环**。目标类别固定为 `Normal`、`Severe Slugging (3)`、`Flow Instability (4)`、`Hydrate in Service Line (9)`，输入固定为 7 个核心变量，默认窗口为 180 秒。

本阶段不把完整 3W 数据、训练集、模型私有凭据或服务器配置提交到 Git；不在 2C2G ECS 上训练；不引入 pgvector、RAG、LLM、Kafka、Redis 或 Kubernetes。TCN 是下一阶段的对照主模型，而不是本阶段的前置条件。

## 当前基线

已完成：

- Git monorepo、FastAPI、Vue 3、PostgreSQL、Mosquitto、WebSocket 和 Edge Agent 骨架；
- ECS 的 HTTPS Web、TLS MQTT、账号 ACL、独立 API/边缘凭据和 Docker Compose 部署；
- API 已通过 TLS 连接 MQTT，网页与 `/api/health` 已验证；
- Pi 上已有 ARM64 Edge Agent 镜像与受限运行时配置，支持心跳、`START`、`STOP`、`PAUSE`、`SET_SPEED`、`LOAD_INSTANCE` 和 1×/5×/10×/20× 回放；ECS 与家庭网之间已有在线 WireGuard，Pi 可经其访问 MQTT 私网端点。

待补齐的 P0 证据：树莓派尚无本地 3W Parquet 实例，因此尚未完成真实遥测、入库、实时曲线与控制命令的端到端演示。此项是本阶段的第一道门槛。

## 工作包

### 1. 数据获取、清单与校验

1. 在 Mac 的 Git 忽略目录下载 Petrobras 3W Dataset 2.0.0，并记录来源、下载日期、目录布局与校验和。
2. 编写 `ml` 下的数据清单/检查脚本：枚举 instance、数据源域、well/instance 标识、事件标签、采样间隔、时间范围、可用变量和缺失率。
3. 定义并测试 7 变量映射：`P_PDG`、`P_TPT`、`T_TPT`、`P_MON_CKP`、`T_JUS_CKP`、`P_JUS_CKGL`、`QGL`。原始列名、单位或缺失模式不符合契约的 instance 必须被显式标记，不可静默填充。
4. 选择至少一个 Normal 和三个目标异常类别的可演示 Parquet instance，复制到 Pi 的挂载数据目录；仅同步所选 instance，不同步完整数据集。

**验收：**生成可提交的匿名化/无原始数据 manifest、变量覆盖率报告与 instance 选择表；Pi 能发现选定的 `.parquet` 文件。

### 2. EDA、标签策略与无泄漏划分

1. 生成 EDA 工件：类别计数、instance/well 数、每变量缺失率、描述统计、代表性趋势图，以及真实/模拟/hand-drawn 域分布。
2. 固定标签字典与未知标签策略；初版只保留 0/3/4/9，其他类别进入排除清单而非混入 Normal。
3. 以 `instance` 为最小分组单元，并在元数据可用时优先按 `well_id` 分组，创建 Train/Validation/Test 划分。不得随机打散时间点。
4. 保存 split manifest、随机种子、数据版本和每一类样本数；以真实油井测试集为主报告，模拟数据可作为训练增强并单独报告域差异。

**验收：**任何一个 instance 只属于一个数据集；脚本可从 manifest 重建相同划分；报告明确说明没有时间序列泄漏。

### 3. 窗口特征与传统模型基线

1. 实现共享特征模块：180 秒窗口、滑动步长配置，以及每变量的 mean、std、min、max、median、range、slope、last value、first difference。
2. 训练仅使用 Normal 窗口的 Isolation Forest，输出 anomaly score、阈值来源和二分类检测指标。
3. 训练 XGBoost：先完成 Normal/Abnormal，再完成 4 分类；处理类别不均衡时使用类别权重和宏平均指标，而不是只优化 Accuracy。
4. 输出 Accuracy、Precision、Recall、Macro F1、每类 Recall、Confusion Matrix、推理延迟及阈值/校准说明。

**验收：**一条命令可训练并评估两个基线；评估不读取测试集以外的数据进行拟合；结果可追溯到固定 split。

### 4. 模型制品、注册与云端推理

1. 为每个模型导出版本化制品目录：模型文件、`metadata.json`、特征 schema、7 变量顺序、窗口/步长、类别映射、数据 manifest 哈希、代码 commit、训练参数和指标。
2. 在 API 中实现只读模型加载与滑动窗口推理：当一个 well 积累足够窗口时产生预测、置信度和异常分数；不足窗口时返回明确的 `warming_up` 状态。
3. 新增 `inference_results` 持久化、最新推理/历史推理 API 与 WebSocket `inference` 事件。ECS 只加载小型 XGBoost 制品并单 worker 推理。
4. 将现有基础阈值告警升级为“模型结果 + 明确规则”的可审计状态机；报警仅作辅助分析，界面和 API 均展示免责声明。

**验收：**重启 API 后可从模型元数据恢复推理；每条推理都能定位到 telemetry 窗口、模型版本和输入 schema。

### 5. 端到端演示与自动化验证

1. 在 Pi 用至少一个选定 instance 做 10×、20× 回放，核对 MQTT ACL、TLS、心跳、控制指令与断线状态。
2. 验证 `START → telemetry → PostgreSQL → WebSocket → Vue 曲线 → inference → alarm`；再验证 `PAUSE`、`SET_SPEED`、`LOAD_INSTANCE`、`STOP` 的往返。
3. 增加单元/集成测试：列映射、窗口边界、group split、特征维度、制品元数据、模型加载、推理 API、重复 sequence 去重和 MQTT 控制契约。
4. 保存一份无秘密的 demo runbook：部署前置条件、所选 instance、启动顺序、预期页面状态、故障定位和截图/指标证据。

**验收：**从干净环境和受控数据挂载可复现完整链路；10×/20× 下无进程崩溃、无未授权 topic，且曲线与模型状态持续更新。

## 顺序、责任与产物

| 顺序 | 工作 | 执行位置 | 主要产物 |
| --- | --- | --- | --- |
| 1 | 数据下载、manifest、列校验 | Mac | `ml` 脚本、数据卡、实例选择表 |
| 2 | Pi 实例挂载与回放验收 | Pi + ECS | 可复现 MQTT/数据库/Web 演示 |
| 3 | EDA 与分组 split | Mac | 图表、split manifest、实验记录 |
| 4 | Isolation Forest 与 XGBoost | Mac | 模型制品、指标、混淆矩阵 |
| 5 | 推理/告警接入 | ECS + Web | 推理 API、模型状态和报警证据 |
| 6 | 回归测试与答辩 runbook | 全部 | 自动化测试、演示脚本 |

## 关键风险与决策

- **数据访问或变量不一致：**先以 manifest 和严格 schema 识别问题；缺失变量 instance 不进入 7 变量基线。
- **类别极不均衡：**主指标采用 Macro F1、每类 Recall 和混淆矩阵；保留类别权重与样本数证据。
- **Pi 内存只有 2 GiB：**PyArrow 分批读取、数据以挂载卷提供，禁止整体加载 Parquet。
- **ECS 只有 2C2G：**训练只在 Mac；ECS 只保存窗口、运行单 worker API、推理 XGBoost，模型制品按需部署。
- **Pi 动态公网 IP 与 CGNAT：**不得用 MQTT 安全组 `/32` 白名单，也不得把 8883 开放到公网。通过既有 WireGuard 私网端点连接；Edge 容器以 `MQTT_CONNECT_IP` 解析 `MQTT_HOST`，继续校验证书域名。每次变更 WireGuard 或容器配置后必须做连通性测试。
- **证书续期：**当前手动 DNS-01 证书不自动续期；在到期前重复 DNS 验证，或后续改为最小权限 Cloudflare DNS API token。

## 完成定义

第二步完成时，仓库必须包含可运行的数据/训练/评估/制品/推理代码和无秘密实验记录；Pi 至少成功回放 1 个 Normal 与 1 个异常 instance；云端和前端能持续展示 7 变量、模型状态及可确认报警；XGBoost 的完整测试集指标与推理延迟可复现。之后才进入 TCN、SHAP、RAG 和 LLM 辅助诊断。
