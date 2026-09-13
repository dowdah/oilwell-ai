# Phase A.2 — Database Compatibility Migration Rehearsal

## 结论与放行状态

**备份恢复、两个限定 schema 变更、数据完整性、应用数据访问、锁超时和事务回滚检查通过；启动迁移门禁失败，Phase A.2 未全部通过。**

因此本轮不生成 `database-migration-runbook.md`，不申请生产维护窗口。原因是用户明确要求“只有隔离演练全部通过后”才能生成生产执行提案。本文为演练结果与阻塞说明，不是生产执行授权。

实际发现旧 API 和 C1 均无条件删除并重建 `uq_inference_telemetry_model_mode`。其唯一性定义没有改变，但约束 OID 和支撑索引 OID 确实改变，带来额外 DDL/锁；不能将“最终定义相同”记作“约束未修改”。本次 startup 探测在隔离事务中回滚并核验身份恢复，没有把该额外变更留在迁移基线。

## 1. 环境、版本与范围

- 日期：2026-09-13；证据时间采用 UTC。备份清单时间：2026-09-13T05:51:41.753696+00:00。
- C1：`3e99c99179b0f6ccdabb20066e33e5adedc11cc0`。工作树 `codex/phase-a-verification`；不改功能代码，不处理 C2。
- 生产：PostgreSQL 16.15，x86_64 Alpine。数据库 `oilwell`，public schema。
- 本地：Docker 容器 `oilwell-a2-rehearsal`，PostgreSQL 16.15，镜像 ID `sha256:75f5a96988cdf694a215073c3e9c001b706b371e2f94df3967f2efdec2787f6b`；1 CPU / 512 MiB，端口仅绑定 `127.0.0.1:55442`。现有镜像为 amd64，在 M1 arm64 主机上运行，有架构模拟影响，不能等同 ECS 耗时。
- 三个隔离数据库：`oilwell`（迁移及应用测试）、`rollback_rehearsal`（再次恢复及锁/回滚）、`schema_rehearsal`（schema-only 恢复）。均仅在新本地容器。
- 旧 API：本轮只读复制实际运行容器的 `/app/app` 与静态知识清单。使用复制源码和本地 Python 依赖验证数据访问，不冒充生产镜像端到端运行；未开发或调用诊断功能。
- 生产仅执行只读 SELECT、pg_dump 和文件读取；没有 DDL/DML、重启、部署、回放、state 初始化或生产遥测。运行中的生产心跳仍会正常更新设备状态，备份是 pg_dump 的一致性快照，并非停写快照。

## 2. 生产备份前后确认

数据库大小：11983895 B；telemetry 3817 行；alarms 2 行。

| device_id | min(sequence) | max(sequence) | count |
|---|---:|---:|---:|
| edge-pi-01 | 1 | 1789216640 | 3817 |

备份前、备份后及演练完成后的三次生产只读查询：上述行数、每设备 min/max/count、全部 public 约束和索引定义一致。元数据查询显式 BEGIN READ ONLY，并返回 transaction_read_only=on；pg_dump 会话设 default_transaction_read_only=on、锁等待上限 3s。

真实约束共 19 项，索引共 25 项，详细清单保存在 `production-before.json`。包括：

- `uq_telemetry_device_sequence UNIQUE(device_id, sequence)` 及同名唯一 B-tree 索引。
- `uq_inference_telemetry_model_mode UNIQUE(telemetry_id, model_mode)` 及同名唯一 B-tree 索引。
- 七表主键、现有外键，以及 telemetry 的 device_id/timestamp/well_id 索引等均保留；恢复与迁移后所有索引 indisvalid/indisready 均为 true。

## 3. 已执行备份及恢复方法

正式本地保留位置（已验证 Git ignored）：
`/Users/sheldon/Documents/codex-projects/oilwell-ai/docs/.local/backups/phase-a2-20260913/`

目录权限 700，production.dump、production-schema.sql、manifest.json 权限 600。SSH 流直接落盘，无生产临时备份文件。工作树忽略目录另留相同 SHA-256 的演练副本，并以只读挂载传入容器。备份含生产数据，不进入 Git，不在报告中附原始传感器值或凭据。正式本地副本避免依赖 /tmp，但不是异地容灾备份；生产维护时仍须重新备份并验证。

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| production.dump | 272730 | `71d1534b0dae3c84f9ee70169df38fdbf18b757b6509c1ee08051d6e477cd765` |
| production-schema.sql | 14417 | `4796d79bd6681d378359a23246025f485783a93ce5148a05920f2b73c00f06f5` |

实际 pg_dump 通过现有 ECS PostgreSQL 容器执行（用户、库名由现有配置在进程内取出，不输出密码）：

```sh
pg_dump --lock-wait-timeout=3s -U "$DB_USER" -d "$DB_NAME" -Fc
pg_dump --lock-wait-timeout=3s -U "$DB_USER" -d "$DB_NAME" --schema-only
```

两次 pg_dump 各自拥有一致性快照，不声称二者共享同一导出 snapshot。备份前后元数据/业务计数无变化；恢复后的 schema 断言再次核实。custom-format 是该数据库的 schema+data 完整备份，不含集群全局角色/密码；隔离环境预建同名 owner `oilwell`，未来恢复需保证角色存在，不能无意修改生产角色。

本地实际恢复命令（仅适用于本轮新建空库）：

```sh
docker exec oilwell-a2-rehearsal pg_restore --exit-on-error --single-transaction   -U oilwell -d oilwell /backup/production.dump
docker exec oilwell-a2-rehearsal createdb -U oilwell rollback_rehearsal
docker exec oilwell-a2-rehearsal pg_restore --exit-on-error --single-transaction   -U oilwell -d rollback_rehearsal /backup/production.dump
docker exec oilwell-a2-rehearsal createdb -U oilwell schema_rehearsal
docker exec oilwell-a2-rehearsal psql -X -q -v ON_ERROR_STOP=1   -U oilwell -d schema_rehearsal -f /backup/production-schema.sql
```

三次恢复均成功；第二次 full 恢复的所有业务行哈希、列定义、约束/索引定义、设备计数与首次恢复迁移前一致。未使用 `--clean`，未覆盖生产库。

## 4. 隔离迁移与完整性验证

执行前从 information_schema 断言 public.telemetry.sequence.udt_name=int4、public.alarms.resolved_at 不存在；否则脚本在 BEGIN/ALTER 前停止。本次断言通过。

实际仅提交以下两条 schema 变更：

```sql
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE public.telemetry
  ALTER COLUMN sequence TYPE BIGINT USING sequence::bigint;
ALTER TABLE public.alarms ADD COLUMN resolved_at TIMESTAMPTZ;
COMMIT;
```

| 验证项 | 结果 |
|---|---|
| telemetry/alarms 行数 | 3817/2，迁移前后相同 |
| 每设备 min/max/count | 全部相同 |
| 全部原始业务字段 | 七表逐行规范 JSON 排序后的 SHA-256 相同；比较排除仅新增的 resolved_at |
| 原有 sequence 数值 | 包含在整行哈希中，全部保持不变 |
| sequence 类型 | int4→int8；原 NOT NULL 保持 |
| resolved_at | timestamptz、nullable YES；存量行均为 NULL |
| 列变化白名单 | 恰好上述两个项目；其他列定义不变 |
| 全部外键/约束/索引定义 | 相同；validated/ready/valid 均正常 |
| 推理复合唯一约束 | 迁移本身未改变约束 OID/索引 OID，也未改变定义 |

首次恢复行数：wells=2，edge_devices=1，telemetry=3817，alarms=2，alarm_states=2，inference_results=7634，diagnostic_records=29。上述比较在添加任何应用测试样本之前完成；后续本地测试样本不混入迁移完整性比较。

## 5. 应用兼容检查

HTTP 使用真实 FastAPI 路由与真实 PostgreSQL 的 ASGI transport；关闭 lifespan 自动运行，避免加载模型和连接 Broker。另单独提取 lifespan 的原始数据库启动语句，在显式事务内执行后回滚。未通过禁用或改写某条 DDL 来隐藏副作用。

| 场景 | 实际结果 |
|---|---|
| 旧 API 读取历史 BIGINT 列中的 int4 范围值 | wells/dashboard/历史遥测/alarms 均 HTTP 200 |
| 旧 API 原范围写入 | 隔离设备 A2-old、sequence=1900000000，POST 202 accepted=true，历史回读一致 |
| 旧 API 重投去重 | 第二次相同 packet accepted=false |
| C1 读取旧历史 | 相同四个 GET 均 200 |
| C1 大整数写入 | A2-c1、sequence=1789300000000000，超过 int4 且小于 JS safe integer 上限；POST 202，回读精确相同 |
| C1 重投去重 | 相同 packet accepted=false |
| C1 报警恢复 | 两个固定异常结果触发、人工确认、三个 Normal 后 RESOLVED 且 resolved_at 非空 |
| C1 启动无额外约束操作 | **失败**，见下 |

报警采用标记为 A2-ISOLATED-FIXTURE 的固定推理结果，仅用于隔离数据库状态机测试，不训练模型，不将其当成真实预测或实机闭环证据。旧版不要求支持大 sequence，也未将此作为旧版能力验证。

### 启动门禁的直接证据

| 源码 | 启动前 (constraint OID, index OID) | 执行启动 SQL 后 | 回滚核验 |
|---|---|---|---|
| 旧 API | [16465, 16464] | [16549, 16548] | 恢复原 OID |
| C1 | [16465, 16464] | [16551, 16550] | 恢复原 OID |

两者均执行：

```sql
ALTER TABLE inference_results DROP CONSTRAINT IF EXISTS uq_inference_telemetry_model_mode;
ALTER TABLE inference_results ADD CONSTRAINT uq_inference_telemetry_model_mode
  UNIQUE (telemetry_id, model_mode);
```

本轮不启动完整 API/MQTT 服务，因此不声称完整启动通过。精确执行的数据库启动段已足以证明违反“不得顺带修改其他约束”的边界。旧 API 同样存在该行为；后续维护计划不能简单写成“停止并重新启动旧 API”而忽略这组 DDL。

## 6. 锁、重写与回滚证据

| 指标 | 隔离实测 |
|---|---|
| sequence ALTER | 61.49 ms |
| resolved_at ALTER | 2.10 ms |
| 事务整体 | 72.01 ms |
| telemetry heap | 786432 → 1048576 B |
| telemetry indexes | 450560 → 483328 B |
| telemetry filenode | 16417 → 16538，证实表重写 |
| 本地数据库大小 | 12024855 → 12336151 B |

无竞争主迁移未报错或超时；未把这一次执行当成并发负载证明。锁场景在第二隔离库中用 ACCESS SHARE 持锁，观察迁移连接 wait_event_type=Lock、wait_event=relation，约 3009.0 ms 后返回 SQLSTATE 55P03。随后 ROLLBACK，列、数据、约束/索引身份、表 filenode 均恢复/保持原样。

另执行两个 ALTER 成功后主动 ROLLBACK，核验同样无残留；第二恢复库仍保留原 int4 schema。备份重恢复和事务回滚两条路径均已验证。全部耗时仅适用于本地容器，不能冒充 ECS 2C2G 生产窗口。

## 7. 阻塞处理建议（未实施）

下一步需单独确认最小修复范围：C1 `apps/api/app/database.py` 的 `migrate_schema`，及 `apps/api/tests/test_postgres_integration.py` 中针对真实已有约束的回归验证。现有复合唯一约束定义正确时保持不动；缺失时才新增；存在不同定义时停止并显式报告，不能静默重建。不顺带修改模型、阈值或其他 schema。

验证应使用本轮生产备份重新恢复库，比较启动前后全部约束/索引 OID 与语义，以及重复启动结果；回归大整数去重和报警恢复。修复只有另行批准才执行，独立 commit；回滚为撤销该独立修复提交，不 reset 原工作区。

旧部署启动代码的同类风险还需纳入单独维护方案：要么提出受控的最小兼容修复并验证，要么在明确可验证的“不触发旧启动 DDL”停写/恢复方案下操作，不能绕过门禁或擅自扩大本次两个 schema 的范围。

所有门禁通过后才编写 production runbook，届时必须重新确认 preflight、各写入者停写与积压、当次备份、schema 断言、两条 SQL、数据/约束比较、旧 API 检查、回滚条件及方法、服务恢复顺序。本轮不预先批准生产窗口。

## 8. 下一阶段 Edge state 算法（仅说明）

```text
停止同 device_id 的所有写入者，并确认没有仍在入库的积压
M = 此时重新查询生产 MAX(sequence)；无行时按初始下界处理
U = 经验证的现有 state.reserved_until；无 state 时为 0
reserved_until = max(M, U)
原子持久化 schema=1 的 state，并 fsync 文件/目录
```

不得使用本报告的 1789216640 作为未来固定种子。C1 随后从 max(当前微秒时间, reserved_until)+1 发号，并先预留 10000；检查不超过 9007199254740991。需稳定 /state 卷、单写入者、禁止旧快照降低高水位。本轮没有创建生产 /state、初始化 sequence、部署 Edge 或重启 Pi。

## 9. 证据、保留与回滚边界

本地原始证据：`docs/.local/phase-a/rehearsal-20260913/`，Git ignored。未提交数据库备份、测试样本或复制的旧源码。演练结束停止本轮独立容器，保留卷和三个数据库；不影响其他本地/生产容器。保留原工作区 52 个 C2 文件及本轮开始前已有的审计文档编辑。

新增的可提交文件仅本报告。撤销本报告提交即可回滚文档；无生产变更需要回滚。

| 关键证据 | SHA-256 |
|---|---|
| `production-before.json` | `3ca3d2ec0bd44c1506158d1a531a7357e73e4dcefcf8e368e9ccb418439fb7c2` |
| `production-after.json` | `3ca3d2ec0bd44c1506158d1a531a7357e73e4dcefcf8e368e9ccb418439fb7c2` |
| `production-final.json` | `3ca3d2ec0bd44c1506158d1a531a7357e73e4dcefcf8e368e9ccb418439fb7c2` |
| `migration-result.json` | `83a41996fff9fac003c3549e95f9625dce099c9b00ed545f701662b4c7d009b1` |
| `old-api.tar` | `e378649fe00e408567070b589f00309239995d4b772cbcd5809f8fe41bbf2605` |
| `old-application.json` | `4956c524fff46ac10042ce0832f493e3721cb05746100711276a15f47b5332d5` |
| `c1-application.json` | `9c0a825e07c20bf51af5d36e6f6a8258ab5f9f2dc390cbac14c47c96e136c17b` |
| `rollback-lock-result.json` | `22d4b9c28e035e65d3bf4f5c6bdd052fd53dd9e21558c23ec965840106ff5344` |
| `schema-restore.log` | `37da8b72da03e6f6dfb3aa757433c3585d8d5d26261aba30f888a7605f66ca6c` |
| `rehearse.py` | `d399c51341662824e8d849b54e35061bce8ddb9f985e78c049d4e87621bc0faa` |
| `app_check.py` | `d0f2044b2b35fe2a51aa15ef922049a4d454eac9f97f045e0d85268e13fb8c06` |
| `risk_check.py` | `cbd805b688d28336577799dd57aa2301c62c5241904f64a5f9ce37d570d40130` |
