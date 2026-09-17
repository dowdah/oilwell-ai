# Final Limitations

## Dataset

当前本地仅有 55 个可读 3W 实例；旧 187-instance 协议无法在这份本地副本上复现。完整审计见 `docs/phase-b/available-data-audit.md`。

## Domain Shift

冻结验证集的高分没有泛化到 held-out `WELL-00014`。Binary XGBoost 的最终一次测试结果为：

| Metric | Value |
| --- | ---: |
| Precision | 1.0000 |
| Recall | 0.0249 |
| Abnormal F1 | 0.0485 |
| Macro F1 | 0.1760 |
| ROC-AUC | 0.4574 |

混淆矩阵为 `[[4923, 0], [22598, 576]]`。这说明 validation 性能不能代表跨井泛化能力。

## Model Use

Phase B binary candidate 状态为 `rejected`，从未部署。不得将实验模型描述为可靠的工业故障诊断能力；当前系统只展示 `Experimental model output` 作为辅助证据。

## LLM

- only advisory；不输出自动控制指令。
- 输入受检索证据和窗口统计约束，不读取完整原始时序。
- citations 只能来自本次 retriever 返回集合。
- 外部兼容 API 不可用时返回模板报告和 `LLM analysis unavailable`。

系统是教学和人工辅助分析系统，不用于自动控制或生产决策。
