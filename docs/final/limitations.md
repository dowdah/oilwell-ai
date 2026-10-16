# Final Limitations

## Dataset

当前本地仅有 55 个可读 3W 实例；旧 187-instance 协议无法在这份本地副本上复现。完整审计见[数据审计](../phase-b/available-data-audit.md)。

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

- 仅作辅助分析，系统不执行现场控制；模型文字仍需人工核验，不能把提示词约束当成形式保证。
- 外部输入为窗口统计、模型结果、报警摘要与引用元数据，不发送完整原始时序或知识文档全文。
- 结构化 citations 和 References 由系统按本次 retriever 返回集合生成。
- 外部兼容 API 不可用时返回模板报告和 `LLM analysis unavailable`。
- 同窗口 SHAP 缺失时，即使 LLM 调用成功也保留证据降级状态。
- 多次回放同一采样时间会保存多个接收序列；当前诊断统计按井和采样时间查询，未按回放批次隔离，样本数可能超过单个窗口的采样数。
- 外部调用有费用；当前限制单次输出长度，未提供全站每日费用上限。公开诊断入口的访问控制与限流应按实际使用范围另行管理。

## Retrieval and deployment

- 当前检索仅匹配受审阅静态知识清单；未提供文档上传、embedding、pgvector 或 FAISS 索引。
- 验收按日期与环境区分，见 [测试矩阵](test-matrix.md)。只读健康检查和历史报告可读不等于新一轮完整回放或外部调用通过。
- 源码包不含数据、模型和凭据，不能开箱复现完整演示；外置材料与平台要求见 [交付清单](delivery-manifest.md)。当前 API 依赖目标为 Linux amd64 / Python 3.12。
- 任何重新部署都必须重新验证制品、数据库、MQTT、WebSocket 与浏览器路径。

系统是教学和人工辅助分析系统，不用于自动控制或生产决策。
