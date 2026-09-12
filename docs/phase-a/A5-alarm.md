# A5 Alarm lifecycle

基准：`3e99c99179b0f6ccdabb20066e33e5adedc11cc0`。分支：`codex/phase-a-verification`。运行编号：`phase-a-20260913`（北京时间 2026-09-13；UTC 记录落在 2026-09-12）。本次只提交验证文档，未修改功能代码。

原始证据位于本工作树忽略目录 `docs/.local/phase-a/run-20260913/`，不包含在 Git 提交中。下面的“通过”均限定测试场景；本地固定样例、真实数据回放、旧部署结果分开记录。

## 结论

本地状态机与 UI 确认/恢复通过；真实模型异常报警未验证。

## 验证与边界

- PostgreSQL 回归验证连续 2 个 active 异常窗口触发、持续异常不重复、人工确认、连续 3 个 Normal 恢复、恢复后再次触发、缺口中断连续证据、shadow 隔离。
- 单独的本地 PHASE-A-FIXTURE 使用固定推理结果，不是训练或真实推理；模型版本显式标为 PHASE-A-UI-FIXTURE-NOT-MODEL-EVIDENCE。
- 浏览器确认报警后显示 ACKNOWLEDGED，独立 WS 收到相同 alarm id 的 alarm_updated；注入 3 个固定 Normal 后页面加载/刷新显示 RESOLVED，resolved_at 已持久化。
- 本次真实 Normal 回放没有异常触发；实机没有新预测证据。不提供虚构报警延迟或检测延迟，不把缺失指标填零。fixture 时间也不当作真实检测延迟。

证据：`a3-a6-regression.log`、`ui-fixture.json`、`ui-ack-event.json`、`ui-resolved.json`、`browser-observations.json`。

## 修改与回滚

未修改本阶段功能代码。只提交本文；撤销文档提交不影响服务。原工作区和 C2 未改动。
