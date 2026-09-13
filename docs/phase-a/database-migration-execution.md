# Phase A.2 生产数据库迁移执行记录

## 维护信息

| 项目 | 记录 |
|---|---|
| Maintenance ID | `phase-a2-20260913T0636Z` |
| Runbook commit | `b298a14` |
| 执行时间（UTC） | 2026-09-13 06:36:35Z–06:42:27Z |
| 最终判定 | **Abort — 未执行 schema migration** |
| DDL COMMIT | **否** |

本记录只保留可公开的执行结论。凭据、备份内容、原始命令输出和运行证据均保留在受控运维通道，不进入 Git。

## 已完成阶段与结果

| Runbook 阶段 | 结果 |
|---|---|
| Preflight A | 通过：PostgreSQL 16.15；资源状态可接受；`telemetry.sequence` 为 `int4`；`alarms.resolved_at` 不存在；目标 UNIQUE 约束定义、有效性和索引状态正确。 |
| Stop Writes — Pi replay STOP | 已发送 `STOP`；现有控制路径返回 `202` queued 回执。随后设备状态为 `ONLINE`，报告 sequence 未增加。 |
| Drain / Stable Verification | **失败 / Abort**：一条用于记录 aggregate telemetry 稳定性的只读 SQL 因未限定的 `device_id` 列名歧义失败。按 Runbook 的任意 SQL error Abort 条件，未修正或重试。 |
| Fresh Production Backup | 未开始。 |
| Final Schema/Data Assertion | 未开始。 |
| Approved DDL | 未执行。 |
| Post-Migration Database Validation | 不适用。 |

## Preflight 基线

- telemetry / alarms / inference_results 行数：3817 / 2 / 7634。
- `edge-pi-01` telemetry：count 3817、min sequence 1、max sequence 1789216640；迁移前 sequence signature 为 `8b4d8d24f16f63adcee06ad8c59e577f`。
- `uq_inference_telemetry_model_mode`：`UNIQUE (telemetry_id, model_mode)`；constraint OID `24613`，backing-index OID `24612`，均 valid/ready。
- `uq_telemetry_device_sequence`：`UNIQUE (device_id, sequence)`；constraint OID `16408`，backing-index OID `16407`，均 validated/valid/ready。
- 初始 MQTT 只读观察未接收到 telemetry；在允许的观测范围内未发现 retained telemetry。该证据未被用作完成 Drain 的依据，因为随后发生了 SQL error。

## Abort 详情与当前状态

触发 Abort 的错误为只读 aggregate 查询中的 `column reference "device_id" is ambiguous`。该连接使用 `BEGIN READ ONLY`；没有执行批准 DDL、没有 `COMMIT`，也没有 schema 或数据修改。

为遵守停止规则，未继续执行 `docker compose stop api`、未创建生产备份、未重新运行查询、未修改 SQL，也未执行 C1 部署、Edge `/state` 初始化、旧 API 重启或任何生产遥测发送。

当前可确认状态：

- database：仍为迁移前 schema（`telemetry.sequence=int4`，`alarms.resolved_at` 不存在）；
- old API：仍运行（未到达 Runbook 中只停止 API 的步骤）；
- Pi replay：已发出 STOP 请求并收到 queued 回执；本次未取得可接受的完整 drain Go 证据；
- telemetry writers：不得视为已获恢复授权；
- C1：未部署；
- `/state`：未初始化。

后续如需再次执行，必须获得新的明确生产执行授权，并从 Preflight A 重新开始；不得把本次的中间证据、未创建的备份或停止请求当成新的 Go 条件。
