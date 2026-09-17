# 8–10 分钟课程 Demo 脚本

## 0:00–0:30 — 项目背景

说明油井生产监测同时涉及边缘设备、实时遥测、云端存储、AI 分析和人工决策支持。

## 0:30–1:20 — 架构图

展示 `system-architecture.md`：树莓派 Edge、MQTT、FastAPI、PostgreSQL、AI inference、WebSocket、Vue 与受控 RAG/LLM 的边界。

## 1:20–2:00 — Dashboard

打开 Dashboard，说明当前井、设备状态、报警计数和实时更新入口。

## 2:00–3:00 — 历史数据与七变量曲线

展示历史页或监测页的 7 个变量曲线与时间窗口。强调使用真实回放/已有历史记录；不要为演示制造假报警。

## 3:00–4:00 — Edge / MQTT / Cloud

说明 3W replay 从 Edge Agent 经 MQTT 到 API，再持久化 PostgreSQL 并推送 WebSocket 的数据路径。

## 4:00–5:00 — AI inference

展示 active 与 shadow 的同窗口结果。说明 active 是工程监测证据，shadow 只作对照；模型输出标记为 `Experimental model output`。

## 5:00–6:40 — Diagnostics 与 RAG

在 Diagnostics 页面选择一个已有 active 推理窗口，展示窗口统计、报警摘要、检索资料、References 和 limitations。说明引用来自本次实际检索，而非 LLM 自行生成。

## 6:40–7:10 — LLM 降级

说明外部兼容 API 未配置或不可用时，页面仍显示模板报告与 `LLM analysis unavailable`；实时监控和历史功能不受影响。

## 7:10–8:30 — Phase B 研究结论

展示 Binary XGBoost 的 held-out `WELL-00014` 结果：Recall 0.0249、F1 0.0485。说明没有泄漏测试集、没有继续调阈值或部署该模型，结论是 rejected。

## 8:30–10:00 — 总结

总结完成的工程闭环：边缘采集、MQTT、云端 API、PostgreSQL、AI、实时 Web、受约束 RAG/LLM 辅助分析。项目亮点是承认并保留模型泛化边界，而不是让不可靠模型自动做工业决策。

若现场不适合运行 replay，使用已有历史数据、已保存的 inference/diagnostic 记录和架构图完成同一叙事，不伪造实时状态。
