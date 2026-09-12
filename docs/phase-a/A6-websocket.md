# A6 WebSocket

基准：`3e99c99179b0f6ccdabb20066e33e5adedc11cc0`。分支：`codex/phase-a-verification`。运行编号：`phase-a-20260913`（北京时间 2026-09-13；UTC 记录落在 2026-09-12）。本次只提交验证文档，未修改功能代码。

原始证据位于本工作树忽略目录 `docs/.local/phase-a/run-20260913/`，不包含在 Git 提交中。下面的“通过”均限定测试场景；本地固定样例、真实数据回放、旧部署结果分开记录。

## 结论

本地已测场景通过；旧部署新遥测未验证/采集超时。

## 验证与边界

- 两个本地 WS 客户端接收相同的真实遥测 sequence；断开第二个客户端后，第一个仍收到 13 条新数据。
- 真实 active inference 与 telemetry/window/model 关联可追溯；手工确认固定报警产生可序列化的 alarm_updated，日期字段正确传输。
- 本地 realtime 单元测试覆盖 JSON 日期与缓存；隔离 Nginx 停止后页面提示“连接中断，正在重连”，恢复后未刷新页面即显示“实时连接正常”。
- 实机采集期间未收到新遥测。由于序列号冲突、固定井 ID 问题在上游已成立，不能单凭零 WS 消息断定生产 WS 自身独立故障。
- 本次没有用真实异常预测触发新 alarm 广播，故该跨层路径仍为未验证，不以 alarm_updated 代替。

证据：`local-chain.json`、`a3-a6-regression.log`、`ui-ack-event.json`、`browser-observations.json`、`deployed-replay.log`。

## 修改与回滚

未修改本阶段功能代码。只提交本文；撤销文档提交不影响服务。原工作区和 C2 未改动。
