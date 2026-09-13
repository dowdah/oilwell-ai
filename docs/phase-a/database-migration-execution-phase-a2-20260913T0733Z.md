# Phase A.2 生产数据库迁移执行记录：phase-a2-20260913T0733Z

## 维护结果

| 项目 | 记录 |
|---|---|
| Maintenance ID | `phase-a2-20260913T0733Z` |
| Runbook commit | `7fda651` |
| 执行时间（UTC） | 2026-09-13 07:33:22Z–07:38:08Z |
| 最终判定 | **Abort — 未执行 schema migration** |
| DDL / COMMIT | **均未执行** |
| 生产备份 | 未创建；因此无本次 SHA-256 或备份元数据 |

本记录只保存公开的执行结论。凭据、连接信息、原始审计输出、broker 日志和备份内容均不进入 Git。

## 各阶段结果

| Runbook 阶段 | 结果 |
|---|---|
| Preflight A | Go：新窗口只读观察到 PostgreSQL 16.15；`telemetry.sequence=int4`；`alarms.resolved_at` 不存在；两项目标 UNIQUE 约束定义/有效性正确。行数为 telemetry 3817、alarms 2、inference_results 7634。 |
| Stop Writes — Pi replay | 已取得新的 `STOP` queued 回执；随后设备心跳为 `ONLINE`，报告 sequence 未增加。 |
| Drain / Stable Verification | Go：按 `7fda651` 提交的 Drain / Stable snapshot 运行三次（07:34:51Z、07:35:38Z、07:36:08Z）；每次 `transaction_read_only=on`、telemetry total 3817、`edge-pi-01` count 3817 / max sequence 1789216640、active telemetry write transactions 0。 |
| Broker drain | clean-session 观察 12 秒：telemetry messages 0、retained telemetry messages 0；审计客户端随后断开。 |
| `docker compose stop api` | **失败 / Abort**：Compose 在服务操作前解析失败，报告 `MQTT_BIND_IP` 未设置；未执行 API stop。未补环境变量、未改用其他命令、未重试。 |
| Fresh Production Backup | 未开始。 |
| Final Schema/Data Assertion | 未开始。 |
| Approved DDL | 未执行。 |
| Post-Migration Database Validation | 不适用。 |

## Preflight catalog 基线

- `uq_inference_telemetry_model_mode`：`UNIQUE (telemetry_id, model_mode)`；constraint OID `24613`，backing-index OID `24612`，valid/ready。
- `uq_telemetry_device_sequence`：`UNIQUE (device_id, sequence)`；constraint OID `16408`，backing-index OID `16407`，validated/valid/ready。
- 唯一 device 的 telemetry count/min/max sequence：3817 / 1 / 1789216640。
- Postgres、API、Mosquitto 与 Web 在 Preflight 时均运行；资源观察未见本次 Go/No-Go 异常。

## Abort 与最终状态

Abort 原因是获批准的 API stop 命令未能在识别出的 Compose working directory 中解析配置；错误发生在服务操作前。由于 Stop Writes 未完整通过，本次不会进入备份或 DDL，也不会修复 Compose 配置、注入环境变量或以容器级命令替代 Runbook 指定命令。

最终状态：

- database：仍为迁移前 schema；
- old API：未由本次维护停止（停止命令未执行）；
- Pi replay：本次已发送 STOP 请求并收到 queued 回执，但本窗口未达成完整 Stop Writes Go；
- telemetry publishers：未获得恢复授权；
- C1：未部署；
- `/state`：未初始化。

任何后续生产执行均须使用新的 Maintenance ID，从 Preflight A 重新开始；本次证据、STOP 请求或任何阶段性结果均不得复用为 Go 条件。
