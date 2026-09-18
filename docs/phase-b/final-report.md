# Phase B — 当前可读 3W 二分类结论

## 结论：rejected

- Candidate status: `rejected`
- Deployment status: `never deployed`
- Test set: Phase B 当前可读数据协议下仅用于最终 held-out 评估一次。
- Historical C2 result: `not reproduced under the current local dataset copy`。
- 模型失败不阻塞课程系统交付；它只限制该候选作为跨井异常检测器或生产模型使用。

本轮没有得到可用的跨井 Normal / Abnormal XGBoost 候选。候选与阈值仅使用训练井和验证井固定，最终对 held-out `WELL-00014` 的一次评估显示异常检测明显退化，因此停止模型优化；不训练候选 2/3，不重用测试集选择模型或阈值，也不接入任何生产组件。

## 冻结协议

- selection SHA-256：`b18806287d5c1dad5c4e3b2572b9645b94c209b47a049b1cbf522786361c1545`
- split SHA-256：`d114ac3b0763ee53ad06fb970fa35acaf52b161a700c537ed030740b116c69d6`
- 特征：7 variables、180 秒窗口、10 秒步长、63 statistical features。
- 井级划分：train `WELL-00001, WELL-00006, WELL-00015, WELL-00016, WELL-00037, WELL-00038`；validation `WELL-00007, WELL-00020`；test `WELL-00014`。
- 当前可读 selection 为 55 个实例。完整覆盖、文件 SHA-256、连续时长、全零变量与排除项见 [available-data-audit.md](available-data-audit.md)；分组与窗口数见 [data-protocol.md](frozen/data-protocol.md)。

## 候选与阈值

唯一候选是 C2 既有的四源标签 class weighting binary XGBoost；没有新增特征、网络、数据扩展或参数搜索。验证集最大化 abnormal F1 的阈值为 `0.0618476532`：

| 集合 | Abnormal Precision | Abnormal Recall | Abnormal F1 | False positive rate |
| --- | ---: | ---: | ---: | ---: |
| Validation | 0.9435 | 1.0000 | 0.9710 | 0.0240 |
| Held-out test | 1.0000 | 0.0249 | 0.0485 | 0.0000 |

最终测试混淆矩阵（行：真实 Normal/Abnormal；列：预测 Normal/Abnormal）为 `[[4923, 0], [22598, 576]]`，Macro F1 为 `0.1760`。PR-AUC 为 `0.8339`，但在异常占多数的该测试井上并不表示阈值可用；ROC-AUC 为 `0.4574`。唯一测试井的逐井结果与全局结果相同。

## 能力边界与制品

- 验证集没有 class 3，且测试仅为 `WELL-00014`；不能据此主张任一异常类型或整体异常检测的稳定跨井泛化。
- 该结果否定的是当前可读数据、冻结协议和该候选组合，不是对未取得数据的结论。
- 本地离线制品保存在忽略路径 `ml/artifacts/phase-b/binary-candidate/`：`xgboost_binary.json`、`model_metadata.json`、`metrics.json`、`threshold.json`；模型 SHA-256 为 `fd3a5e4014714b52d4bd87e71add404970e3f36befb317188918d11062edc590`。
- 旧 C2 abnormal recall `0.0051782` 仅是未复现的历史记录，不构成当前候选或交付能力证据。

本阶段在此结束；没有修改 API、frontend、database、Edge、MQTT 或 production deployment。
