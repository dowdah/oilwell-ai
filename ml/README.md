# Machine-learning workspace

此目录只在 Mac 本机执行训练。原始数据不进入 Git，也不上传 ECS。

## 固定实验协议

- 先使用 7 个核心变量和 180 秒窗口，stride 取 10–30 秒。
- 使用 instance 或 well ID 做 GroupKFold / 分组 Train–Val–Test；不允许按单个时间点随机切分。
- 首轮类别：Normal、Severe Slugging、Flow Instability、Hydrate in Service Line。
- 顺序：Isolation Forest baseline → XGBoost 窗口统计特征 → TCN。
- 报告 Accuracy、Precision、Recall、Macro F1、混淆矩阵和 CPU 推理延迟；真实井数据优先作为最终测试集。

模型发布到 `ml/artifacts/`（已忽略）时，必须同时提供 `model_metadata.json`，且符合 `model_metadata.schema.json`。API 仅加载经验证的制品，不在 ECS 训练。

## 第二阶段执行顺序

安装依赖后，依次执行以下命令；所有原始数据路径都必须位于 Git 忽略目录。

```bash
python scripts/download_3w.py --source-url '<authorized dataset URL>'
python ml/scripts/inspect_3w.py /absolute/path/to/3w-parquet
python ml/scripts/select_instances.py docs/experiments/3w-manifest.json
python ml/scripts/report_eda.py docs/experiments/3w-manifest.json docs/experiments/3w-instance-selection.json \
  --data-root /absolute/path/to/3w-parquet
python ml/scripts/train_baselines.py docs/experiments/3w-instance-selection.json \
  --data-root /absolute/path/to/3w-parquet
```

前两个工件（manifest 与实例选择表）不含原始时序数据，可以提交以复现实验选择。训练命令会锁定分组 split，写入 `docs/experiments/3w-split.json`，并在 `ml/artifacts/current/` 生成 Isolation Forest、XGBoost、指标和可部署的元数据。将该目录只读挂载到 API 后，重启 API 才会加载新制品。

## 第三阶段：TCN shadow 模型

TCN 必须复用第二阶段生成的 `3w-split.json`，而不是重新划分时间点。安装此目录的依赖后运行：

```bash
python -m pip install -r ml/requirements.txt
python ml/scripts/train_tcn.py docs/experiments/3w-instance-selection.json \
  --data-root /absolute/path/to/3w-parquet \
  --split docs/experiments/3w-split.json \
  --artifacts ml/artifacts/tcn-shadow
```

脚本流式读取 Parquet，每个时刻只保留一个 180 行窗口；标准化参数只由训练组拟合。它写入 Git 忽略的 `tcn_model.pt`、`tcn_config.json`、`scaler.json`、`model_metadata.json` 与 `comparison.json`。Compose 会将此目录以只读方式挂载到 `/models/shadow`；重启 API 后可通过“模型中心”确认 `shadow / ready`。TCN 不参与报警和控制。
