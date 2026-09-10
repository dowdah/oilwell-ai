# Machine-learning workspace

此目录只在 Mac 本机执行训练。原始数据不进入 Git，也不上传 ECS。

## 固定实验协议

- 先使用 7 个核心变量和 180 秒窗口，stride 取 10–30 秒。
- 使用 instance 或 well ID 做 GroupKFold / 分组 Train–Val–Test；不允许按单个时间点随机切分。
- 首轮类别：Normal、Severe Slugging、Flow Instability、Hydrate in Service Line。
- 顺序：Isolation Forest baseline → XGBoost 窗口统计特征 → TCN。
- 报告 Accuracy、Precision、Recall、Macro F1、混淆矩阵和 CPU 推理延迟；真实井数据优先作为最终测试集。

模型发布到 `ml/artifacts/`（已忽略）时，必须同时提供 `model_metadata.json`，且符合 `model_metadata.schema.json`。API 仅加载经验证的制品，不在 ECS 训练。
