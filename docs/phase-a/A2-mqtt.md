# A2 MQTT transmission

基准：`3e99c99179b0f6ccdabb20066e33e5adedc11cc0`。分支：`codex/phase-a-verification`。运行编号：`phase-a-20260913`（北京时间 2026-09-13；UTC 记录落在 2026-09-12）。本次只提交验证文档，未修改功能代码。

原始证据位于本工作树忽略目录 `docs/.local/phase-a/run-20260913/`，不包含在 Git 提交中。下面的“通过”均限定测试场景；本地固定样例、真实数据回放、旧部署结果分开记录。

## 结论

本地通过；实机连接正常，新遥测链路未通过。

## 验证与边界

- 本地独立 MQTT 与 WS 的 241 条初始遥测 sequence 集合一致，源字段逐项一致。
- 仅中断本次测试 Broker；API 检测到 mqtt_connected=false，命令返回 503；恢复后约 4.95 秒重新连接并收到新 STOP applied 回执。
- 实机 health 显示 MQTT 已连，Pi 镜像配置 TLS=true/8883，命令使实例、速度、运行状态发生变化；未关闭 TLS/ACL，也未故障注入共享 Broker。
- 实机旧接口未提供 C1 command_id 回执；仅能按状态变化确认效果。没有取得新遥测 WS 证据，不能把连接正常写成传输验收完成。未独立进行拒绝越权 topic 测试。

证据：`local-chain.json`、`mqtt-recovery.json`、`deployed-before.json`、`deployed-after.json`。

## 修改与回滚

未修改本阶段功能代码。只提交本文；撤销文档提交不影响服务。原工作区和 C2 未改动。
