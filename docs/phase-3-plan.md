# 第三阶段实施计划：TCN 时序模型与对照推理

## 目标与边界

在第二阶段已经验证的 3W 数据工程、Isolation Forest、XGBoost 推理和可审计报警闭环之上，交付可复现的轻量 TCN 四分类模型，并将其作为云端 **shadow inference** 接入系统。

本阶段固定使用 `Normal`、`Severe Slugging (3)`、`Flow Instability (4)`、`Hydrate in Service Line (9)`、7 个核心变量和 180 秒窗口。XGBoost 保持默认活动报警模型；TCN 在通过指标、延迟和资源验收前不产生报警。

本阶段不引入 SHAP、RAG、LLM、pgvector、Kafka、Redis、Kubernetes 或边缘端强制推理。

## 工作包

### 1. 时序数据集与无泄漏预处理

1. 复用第二阶段的 instance/well 分组 split、实例选择表和数据 manifest；不得重新按时间点随机切分。
2. 实现按需读取的 PyTorch Dataset：按 Parquet batch 读取、动态构造 `[channels=7, timesteps=180]` 窗口，默认 stride 为 10 秒，不将全部窗口物化到内存。
3. 仅使用训练集拟合每变量归一化参数；验证集、测试集和线上推理只读取该参数。
4. 将数据版本、split 哈希、标准化统计量和窗口协议写入 TCN 制品元数据。

**验收：**相同 seed 和 split 可复建相同样本集合；任一 instance/well 只出现于一个数据集；测试集不参与归一化拟合。

### 2. TCN 训练与对照评估

1. 实现轻量残差 TCN：三组 Conv1D block，通道为 32/64/64，dilation 为 1/2/4，全局池化后四分类输出；总参数量不超过 100 万。
2. 默认优先使用 Mac 的 PyTorch MPS，无法使用时回退 CPU；训练参数、随机种子、早停条件和最佳 checkpoint 必须记录。
3. 使用类别权重应对不均衡，验证集 Macro F1 用于选择 checkpoint。
4. 对 XGBoost 与 TCN 使用同一测试组，报告 Accuracy、Precision、Recall、Macro F1、每类 Recall、混淆矩阵、真实数据测试子集结果和 CPU 推理延迟。

**验收：**一条命令可训练、评估并复现 TCN；对比报告能追溯到同一 split、数据 manifest 与代码 commit。

### 3. 制品、模型注册与 Shadow 推理

1. 导出版本化 TCN 制品：`tcn_model.pt`、`tcn_config.json`、`scaler.json`、`model_metadata.json` 和评估结果；制品继续保存在 Git 忽略目录。
2. 将 API 推理层抽象为 XGBoost/TCN adapter，按模型版本、类型和输入 schema 校验制品。
3. 保持 XGBoost 为 `active` 模型及唯一报警来源；TCN 为 `shadow` 模型，使用相同滑动窗口写入独立推理结果，但不驱动报警状态机。
4. 推理结果、WebSocket 事件和模型状态需包含模型类型、版本、模式（`active`/`shadow`）和推理延迟，避免两种模型结果混淆。

**验收：**API 重启后可恢复活动 XGBoost 和 shadow TCN；两类结果均可查询、实时展示，且 TCN 不能改变既有报警行为。

### 4. 模型中心与演示证据

1. 新增模型中心页面，显示活动模型、shadow 模型、制品版本、训练数据版本、关键指标、延迟和当前加载状态。
2. 监测页继续显示活动模型结论；模型中心展示同一窗口上 XGBoost 与 TCN 的对照结果。
3. 更新无秘密 demo runbook，记录 TCN 制品部署、shadow 验证、模型对比和回退到 XGBoost 的步骤。

**验收：**答辩演示可展示实时数据、活动 XGBoost 报警、TCN shadow 结论与可复现的离线对照指标。

## 测试与完成定义

- 单元测试：动态窗口边界、变量顺序、训练集归一化、分组 split、TCN 输入形状、MPS/CPU 回退、制品元数据和模型 adapter。
- 集成测试：双模型制品加载、实时推理事件、结果持久化隔离、TCN shadow 不触发报警、活动模型回退到 XGBoost。
- 完成时，仓库包含训练/评估/服务代码、无秘密实验记录、模型对比结果与演示手册；XGBoost 的现有实时推理和报警测试必须保持通过。

## 默认决策

- TCN 仅在 Mac 训练；Pi 继续只承担回放、心跳与控制命令。
- ECS 以单 worker、只读制品和轻量 CPU 推理运行；TCN 先 shadow，只有用户明确确认后才可成为活动报警模型。
- SHAP 在 TCN 对照完成后开始；RAG/LLM 只消费已验证的模型输出和趋势摘要。
