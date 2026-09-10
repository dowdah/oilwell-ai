# 第三阶段演示手册：TCN Shadow 推理

## 前置条件

- 第二阶段的 XGBoost 制品位于 Git 忽略的 `ml/artifacts/current/`，并能以 `active / ready` 载入。
- 使用同一实例选择表和 `docs/experiments/3w-split.json` 训练 TCN；不得重新按时间点划分数据。
- TCN shadow 制品位于 Git 忽略的 `ml/artifacts/tcn-shadow/`，其中包含 `tcn_model.pt`、`tcn_config.json`、`scaler.json`、`model_metadata.json` 和 `comparison.json`。
- API/镜像已安装 `torch`，Compose 的两个模型目录均为只读挂载。

## 部署与验证

1. 在 Mac 运行 `python ml/scripts/train_tcn.py ...`，保存命令、数据版本、split 哈希、checkpoint 的验证集 Macro F1 与 `comparison.json`。
2. 重启 API，访问 `/api/health` 或 `/api/models`；确认 XGBoost 为 `active / ready`，TCN 为 `shadow / ready`，并核对训练数据版本、制品版本和指标。
3. 以同一油井回放正常和异常实例，等待完整 180 秒窗口。实时监测页应只显示 active XGBoost 的结论；模型中心应显示相同 telemetry ID 的 XGBoost 与 TCN 结果、模型模式和推理延迟。
4. 对异常实例，确认报警仅在连续两次 **active XGBoost** 异常结果后出现。TCN 即使输出异常，也不得改变 `Alarm` 或 `AlarmState`。
5. 保存模型中心、监测页、报警中心和 `/api/models` 的脱敏截图；不要记录数据集路径、MQTT 地址、证书或凭据。

## 回退

若 TCN 无法载入、指标不足或延迟超标，保留 active XGBoost 不变，停止 API，移除或修复 `ml/artifacts/tcn-shadow/` 中的制品后再启动。`shadow / unavailable` 是可接受的降级状态；禁止将未审阅的 TCN 目录挂载到 `/models/current`，也禁止改变 active 模型模式来绕过报警验证。
