# 生产数据库迁移 Runbook：Phase A.2

## 0. 执行边界与结论

本 Runbook 只定义一次受控生产数据库维护窗口的操作和判定。它**不是本次会话的执行授权**；本文件的提交、评审或阅读均不得触发生产 SQL、部署、重启或遥测写入。

成功完成本 Runbook 后的唯一状态是：

> **Database ready for C1 deployment**

这不表示 Phase A 通过、C1 已部署、Edge 已就绪或生产验证已完成。后续仍需分别批准：

1. C1 Controlled Deployment Plan；
2. Pi `/state` 初始化；
3. C1 API/Web/Edge 部署；
4. 实机 Phase A 重验。

## 1. 适用版本与前置条件

| 项目 | 适用值 / 要求 |
|---|---|
| C1 基准 commit | `3e99c99179b0f6ccdabb20066e33e5adedc11cc0` |
| 约束迁移修复 commit | `6eb90bb` (`fix: make inference unique constraint migration idempotent`) |
| 最后审计到的 PostgreSQL | PostgreSQL 16.15；这是备份演练时的审计值，不是维护窗口的实时断言，必须在 Preflight 重读 `version()`。 |
| 当前旧 API | 最后审计时为既有生产 API（历史部署基准 `34e69ad`）；其 startup 有已知的 `uq_inference_telemetry_model_mode` DROP+ADD 风险。不得因本 Runbook 重启它。 |
| 当前 Edge | 保持现有已部署版本；不部署 C1 Edge，不初始化或修改 `/state`，维护窗口内 Pi replay 必须停止。 |
| 模型 | 保持维护前的模型、阈值、active/shadow 状态和制品不变；本 Runbook 不加载、更换或验证模型。 |

本次 schema 目标**仅**有两项：

1. `public.telemetry.sequence`: `INTEGER` → `BIGINT`；
2. `public.alarms.resolved_at`: 新增可空 `TIMESTAMPTZ`。

本 Runbook 不包含 C1 Edge、C1 API/Web 部署、sequence state 初始化、模型迁移，以及 Phase B/C/D 的任何工作。不得把历史 sequence 值、演练值或其他固定常数当成未来 sequence 初始化值。

## 2. 变量、证据目录与命令标记

所有生产操作只能由已获授权、具备最小权限的操作员在生产维护窗口执行。连接信息必须来自批准的秘密管理方式；不得把密码、私钥路径、令牌或完整连接串写入 shell 历史、工单正文或 Git。

以下是**示例变量名**，不是可直接复制的凭据或路径：

```bash
# 示例：由批准的秘密管理方式注入；不在此处填写实际值。
export PROD_DATABASE_URL='<secret-provided-at-execution>'
export MIGRATION_BACKUP_DIR='<approved-non-git-backup-directory>'
export MIGRATION_AUDIT_DIR='<approved-non-git-audit-directory>'
export MAINTENANCE_ID='<change-ticket-or-window-id>'
```

本文中的命令按以下标签解释：

- **示例**：说明格式或变量，不可直接作为生产命令执行。
- **经审核可执行命令**：仅在本 Runbook 的前置 Go 条件全部满足、已获得本次生产执行授权后运行。
- **经审核可执行 SQL**：本次唯一允许的生产 DDL；不得拼接、替换或额外执行其他 schema 修改。

所有备份、schema 快照、命令输出和差异文件必须保存在非 Git 的受控目录，权限为 owner-only。不得提交备份、审计输出或任何凭据。

## 3. Go / No-Go Preflight

维护窗口开始前，先由操作员记录开始时间、变更编号、执行人和回滚决策人。以下每项都必须有当前窗口的只读证据；任何一项缺失、超时或与预期不一致即为 **No-Go**，停止并重新评估。

### Go / No-Go checklist

- [ ] 已重新确认生产实例、数据库名、维护窗口和负责人；未使用演练库或旧备份代替生产核验。
- [ ] `SELECT version()` 与已批准的 PostgreSQL 16 系列运行环境一致；版本或托管方式变化已重新评审。
- [ ] 当前 schema 与本 Runbook 的迁移前断言一致：`sequence=int4`、`resolved_at` 不存在。
- [ ] `uq_telemetry_device_sequence` 是 `public.telemetry(device_id, sequence)` 的 UNIQUE 约束。
- [ ] `uq_inference_telemetry_model_mode` 是 `public.inference_results(telemetry_id, model_mode)` 的 UNIQUE 约束，且记录其 constraint OID 与 backing-index OID。
- [ ] 已记录每个 `device_id` 的 telemetry `count/min(sequence)/max(sequence)`，以及 telemetry、alarms、inference_results 行数。
- [ ] 已确认 API、PostgreSQL、MQTT、Edge 的实际运行状态和镜像/版本；历史审计值不能代替本次观察。
- [ ] Pi replay 已停止，且没有相同 `device_id` 的其他 MQTT、HTTP、脚本或人工写入者。
- [ ] PostgreSQL 宿主磁盘空间、容器/宿主 CPU 与内存、连接数、ECS 资源状态均可接受；无磁盘逼近、OOM、重启、复制或存储告警。
- [ ] 已完成本次维护窗口的新备份及其可读性验证。
- [ ] 已批准停写策略，且明确谁负责确认 MQTT 积压、保留消息和所有替代写入路径。

### 经审核可执行只读命令：基础实例与资源核验

在生产数据库宿主或受控运维通道中运行。以下命令不包含凭据；操作员须以已批准的方式提供 `PROD_DATABASE_URL`。

```bash
psql "$PROD_DATABASE_URL" -X -v ON_ERROR_STOP=1 -c 'SELECT version(), current_database(), current_user, now();'
psql "$PROD_DATABASE_URL" -X -v ON_ERROR_STOP=1 -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;"
df -h
docker compose ps
docker stats --no-stream
```

`docker compose ps` 和 `docker stats` 只是在确认状态；必须使用生产环境实际、已批准的 Compose 项目上下文。若无法安全地识别该上下文，停止，不猜测服务名或执行部署命令。

### 经审核可执行只读 SQL：迁移前数据库断言与数据基线

将输出保存为本次审计证据。查询使用 PostgreSQL catalog 的实际约束类型和列顺序，不依赖字符串拆分。

```bash
umask 077
set -o errexit -o nounset -o pipefail
install -d -m 700 "$MIGRATION_AUDIT_DIR"

psql "$PROD_DATABASE_URL" -X -v ON_ERROR_STOP=1 -P pager=off <<'SQL' \
  | tee "$MIGRATION_AUDIT_DIR/${MAINTENANCE_ID}-preflight-schema.txt"
SELECT table_name, column_name, udt_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (table_name, column_name) IN (('telemetry', 'sequence'), ('alarms', 'resolved_at'))
ORDER BY table_name, column_name;

WITH target(name, relation_name) AS (
  VALUES
    ('uq_telemetry_device_sequence', 'telemetry'),
    ('uq_inference_telemetry_model_mode', 'inference_results')
)
SELECT c.conname,
       c.oid AS constraint_oid,
       c.conindid AS backing_index_oid,
       c.contype AS constraint_type,
       n.nspname AS table_schema,
       r.relname AS table_name,
       array_agg(a.attname ORDER BY k.ordinality) AS columns,
       pg_get_constraintdef(c.oid) AS definition
FROM target t
JOIN pg_class r ON r.oid = to_regclass(format('%I.%I', 'public', t.relation_name))
JOIN pg_constraint c ON c.conrelid = r.oid AND c.conname = t.name
JOIN pg_namespace n ON n.oid = r.relnamespace
JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, ordinality) ON TRUE
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
GROUP BY c.conname, c.oid, c.conindid, c.contype, n.nspname, r.relname
ORDER BY c.conname;

SELECT device_id,
       count(*) AS telemetry_count,
       min(sequence) AS min_sequence,
       max(sequence) AS max_sequence
FROM public.telemetry
GROUP BY device_id
ORDER BY device_id;

SELECT 'telemetry' AS table_name, count(*) AS row_count FROM public.telemetry
UNION ALL SELECT 'alarms', count(*) FROM public.alarms
UNION ALL SELECT 'inference_results', count(*) FROM public.inference_results
ORDER BY table_name;
SQL
```

Expected schema rows are exactly:

| Assertion | Expected before migration |
|---|---|
| `telemetry.sequence` | `int4`, not null |
| `alarms.resolved_at` | no row (column absent) |
| `uq_telemetry_device_sequence` | `contype = u`, table `public.telemetry`, ordered columns `{device_id,sequence}` |
| `uq_inference_telemetry_model_mode` | `contype = u`, table `public.inference_results`, ordered columns `{telemetry_id,model_mode}` |

If either constraint is absent, has another type/table/ordered column list, or the expected column state differs, it is **No-Go**. Do not attempt to repair production schema under this Runbook.

## 4. 停写策略

生产写入路径是：

```text
Edge → MQTT → API subscriber → PostgreSQL
```

HTTP ingestion、手工脚本、备用 Edge 或同一 `device_id` 的任何其他 publisher 同样可能绕过这条主路径，必须逐一确认。

### 停写顺序和可验证条件

1. **先停止产生者，而不是先停止数据库。** 使用已批准的 Edge 控制路径停止 Pi replay；若该路径不能给出可靠停止确认，则由负责人员通过受控方式停止 Edge replay 进程，并阻止其自动重启。不要初始化 `/state`、不要改变 sequence、不要部署 C1 Edge。
2. **保持 MQTT 与当前 API 暂时运行以排空并观察。** 不停止 PostgreSQL；不将“服务仍运行”视为无写入证据。记录停止请求、Edge 状态/回执、最后一条接受的 telemetry 以及观察开始时间。
3. **证明写入已经静止。** 在超过当前最大消息间隔、QoS 重试窗口和 API subscriber 处理延迟的连续观察窗口内，重复记录 telemetry 总数、每 device 的 max sequence 和 API/数据库日志；这些值必须稳定。确认 broker 没有对该客户端会话待投递的 QoS 消息、没有 telemetry retained message，且没有重连/自动重放计划。
4. **封闭所有替代写入者。** 明确列出并停止同一数据库的 HTTP 发送器、脚本、备用 Edge 与其他同 `device_id` publisher。若任何写入者无法确认，No-Go。
5. **最后停止或隔离 API 的 MQTT subscriber，但不重启旧 API。** 目的只是防止维护期间继续消费；不要用“restart API”实现此步骤。确认数据库中没有活跃 telemetry 写入事务，且计数/每-device max sequence 再次稳定。

### MQTT 积压和旧消息风险

MQTT 可能因 QoS、持久会话、保留消息或客户端重连在稍后投递旧 telemetry。仅停止 Pi 进程不足以证明安全。必须由 broker 运营证据确认：对相关 telemetry topic 没有 retained message、目标 subscriber 没有未确认积压、没有会在后续重启时重放的会话消息。

在本 Runbook 结束后，**不要**恢复旧 API、旧 Edge 或任何 telemetry publisher。数据库迁移完成后至 C1 受控部署前，写入保持关闭。这样既避免旧 API startup 的额外 DDL，也避免旧消息或旧 sequence 在未完成 C1 Edge state 初始化前进入数据库。

如果无法证明上述任意一点，保持停写并判定 No-Go；不得以重启旧 API “查看健康状态”。

## 5. 当次生产备份

不得复用任何演练备份作为生产迁移备份。维护窗口开始、停写且 Go 后，重新生成以下文件：

- custom-format 全库备份；
- schema-only 备份；
- SHA-256 清单；
- 文件大小、生成时间、工具版本和 owner-only 权限记录。

### 经审核可执行命令：创建与验证本次备份

```bash
umask 077
set -o errexit -o nounset -o pipefail
install -d -m 700 "$MIGRATION_BACKUP_DIR" "$MIGRATION_AUDIT_DIR"

BACKUP_PREFIX="$MIGRATION_BACKUP_DIR/${MAINTENANCE_ID}-before"
pg_dump --format=custom --file "${BACKUP_PREFIX}.dump" "$PROD_DATABASE_URL"
pg_dump --schema-only --file "${BACKUP_PREFIX}-schema.sql" "$PROD_DATABASE_URL"

test -s "${BACKUP_PREFIX}.dump"
test -s "${BACKUP_PREFIX}-schema.sql"
chmod 600 "${BACKUP_PREFIX}.dump" "${BACKUP_PREFIX}-schema.sql"
sha256sum "${BACKUP_PREFIX}.dump" "${BACKUP_PREFIX}-schema.sql" \
  | tee "${BACKUP_PREFIX}-sha256.txt"
stat --format='%n|%s bytes|mode=%a|mtime=%y' \
  "${BACKUP_PREFIX}.dump" "${BACKUP_PREFIX}-schema.sql" \
  | tee "${BACKUP_PREFIX}-metadata.txt"

# 可读性与结构检查：不恢复到生产，不写入生产数据库。
pg_restore --list "${BACKUP_PREFIX}.dump" \
  > "$MIGRATION_AUDIT_DIR/${MAINTENANCE_ID}-backup-toc.txt"
pg_restore --schema-only --file "$MIGRATION_AUDIT_DIR/${MAINTENANCE_ID}-backup-schema-check.sql" \
  "${BACKUP_PREFIX}.dump"
test -s "$MIGRATION_AUDIT_DIR/${MAINTENANCE_ID}-backup-toc.txt"
test -s "$MIGRATION_AUDIT_DIR/${MAINTENANCE_ID}-backup-schema-check.sql"
```

`pg_dump`、`pg_restore --list` 和 schema-only extraction 必须成功，文件必须非空，SHA-256 与大小必须已记录，且权限必须是 owner-only。生产数据量或恢复计划要求更强验证时，必须在独立环境进行恢复演练；不得把恢复验证指向生产实例。备份失败、校验失败或存储位置不满足受控要求均为 No-Go。

## 6. Schema 再断言

备份完成后、DDL 前，重新运行第 3 节的 schema/data baseline 查询，并保存为新的时间戳文件。此次结果必须仍显示：

- `telemetry.sequence = int4`；
- `alarms.resolved_at` 不存在；
- 推理复合唯一约束为 `UNIQUE (telemetry_id, model_mode)`；
- telemetry 唯一约束为 `UNIQUE (device_id, sequence)`。

若从停写后的第一次查询到 DDL 前查询之间存在任何新 telemetry、row count、device max sequence、约束、索引或 OID 意外变化，停止。不得继续执行 SQL 或把差异解释为“正常积压”。

## 7. 正式迁移 SQL

以下是本 Runbook **唯一**获审核可执行的生产 DDL。必须作为一个事务原样执行。不得增加第三项 schema 修改，不得运行应用 startup migration，不得在同一窗口附带索引重建、约束重建、数据更新或清理。

### 经审核可执行 SQL：唯一允许的 DDL

```sql
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '60s';

ALTER TABLE public.telemetry
  ALTER COLUMN sequence TYPE BIGINT USING sequence::bigint;

ALTER TABLE public.alarms
  ADD COLUMN resolved_at TIMESTAMPTZ;

COMMIT;
```

### 经审核可执行命令：受控提交

将上述 SQL 保存为本次受控审计目录中的只读副本，双人复核其内容与本节完全一致后执行。以下命令中的文件由本次维护窗口创建，不能引用历史演练文件。

```bash
psql "$PROD_DATABASE_URL" -X -v ON_ERROR_STOP=1 \
  -f "$MIGRATION_AUDIT_DIR/${MAINTENANCE_ID}-approved-migration.sql" \
  | tee "$MIGRATION_AUDIT_DIR/${MAINTENANCE_ID}-migration-output.txt"
```

出现 `lock_timeout`、`statement_timeout`、任意 SQL 错误、连接中断或不确定提交结果时，立即进入第 10 节，不要重试或替换 SQL。只有明确看到同一会话的 `COMMIT` 成功，才进入 post-migration validation。

## 8. Post-Migration Validation

DDL 成功后，保持所有写入关闭。将迁移前和迁移后快照逐项比较；不可只比较“数据库能连接”。

### 必须相同的项目

- telemetry、alarms、inference_results 行数；
- 每个 device 的 telemetry count/min(sequence)/max(sequence)；
- 全部原 sequence 值（按 `id/device_id/sequence` 的可复算快照）；
- `uq_telemetry_device_sequence` 的定义、constraint OID 和 backing-index OID；
- `uq_inference_telemetry_model_mode` 的定义、constraint OID 和 backing-index OID；
- 其余既有约束、外键、关键索引的定义和 OID。

### 允许且必须出现的变化

- `telemetry.sequence` 为 `int8`/`BIGINT`，原有 NOT NULL 保持；
- `alarms.resolved_at` 为 `timestamptz`，nullable 为 `YES`；
- 存量 alarms 的 `resolved_at` 均为 NULL；
- 没有其他列、约束或索引变化。

特别门禁：本次迁移**不得**修改 `uq_inference_telemetry_model_mode`。其 constraint OID 和 backing-index OID 必须与迁移前一致。

### 经审核可执行只读 SQL：迁移后比较快照

```bash
set -o errexit -o nounset -o pipefail
psql "$PROD_DATABASE_URL" -X -v ON_ERROR_STOP=1 -P pager=off <<'SQL' \
  | tee "$MIGRATION_AUDIT_DIR/${MAINTENANCE_ID}-postmigration-catalog.txt"
SELECT table_name, column_name, udt_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (table_name, column_name) IN (('telemetry', 'sequence'), ('alarms', 'resolved_at'))
ORDER BY table_name, column_name;

SELECT 'telemetry' AS table_name, count(*) AS row_count FROM public.telemetry
UNION ALL SELECT 'alarms', count(*) FROM public.alarms
UNION ALL SELECT 'inference_results', count(*) FROM public.inference_results
ORDER BY table_name;

SELECT device_id,
       count(*) AS telemetry_count,
       min(sequence) AS min_sequence,
       max(sequence) AS max_sequence,
       md5(string_agg(format('%s|%s|%s', id, device_id, sequence), '' ORDER BY id)) AS sequence_value_signature
FROM public.telemetry
GROUP BY device_id
ORDER BY device_id;

SELECT c.conrelid::regclass AS table_name,
       c.conname,
       c.oid AS constraint_oid,
       c.conindid AS backing_index_oid,
       c.contype,
       pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'public'
ORDER BY c.conrelid::regclass::text, c.conname;

SELECT t.relname AS table_name,
       i.indexrelid AS index_oid,
       pg_get_indexdef(i.indexrelid) AS definition
FROM pg_index i
JOIN pg_class t ON t.oid = i.indrelid
JOIN pg_class idx ON idx.oid = i.indexrelid
JOIN pg_namespace n ON n.oid = idx.relnamespace
WHERE n.nspname = 'public'
ORDER BY t.relname, idx.relname;

SELECT count(*) AS existing_alarm_rows_with_resolved_at
FROM public.alarms
WHERE resolved_at IS NOT NULL;
SQL
```

Use a deterministic diff tool to compare the pre/post audit files and attach the result to the change record. The operator must manually verify that the only allowed schema differences are the two listed above. Any row-count, sequence-signature, constraint/index OID, index definition, foreign-key definition, nullability or unexpected schema difference is an Abort condition.

## 9. 应用兼容性检查（不部署 C1）

数据库迁移成功只证明 database readiness；它不授权 C1 deployment。

在 C1 deployment 前，只做当前生产应用的最低必要兼容性检查：已运行实例的只读业务接口、数据库只读查询和受控日志检查。检查必须保持停写，且不得触发 application lifespan。

旧 API startup 存在历史性的 `DROP CONSTRAINT` + `ADD CONSTRAINT` 风险，尤其针对 `uq_inference_telemetry_model_mode`。因此：

- 可以检查已运行 API 的只读 HTTP 路径（例如既有 health、wells、dashboard、telemetry history、alarms），前提是确认这些请求不重启进程、不调用 startup migration、不写 telemetry。
- 可以执行本 Runbook 的 psql catalog/数据只读检查。
- 不得为了“健康检查”重启、重建、滚动更新或 `compose up` 旧 API；这些操作会进入 lifespan 并可能执行额外 DDL。
- 不得恢复 Edge 或发送测试 telemetry；数据库迁移成功不等于 C1 已部署或 C1 Edge 已准备好。

若最低兼容性检查出现数据库错误、schema error、API 读取异常或任何意外 DDL 迹象，保持停写并按 Abort/rollback 条件处理。

## 10. 回滚策略

### A. SQL 尚未 COMMIT / DDL 失败

若事务仍未提交或任一 DDL 失败，直接在同一连接执行 `ROLLBACK;`。确认迁移前 schema/data/catalog 快照仍一致后停止，不要重试。

### B. SQL 已成功 COMMIT，但尚未写入超出 int4 范围的 sequence

优先保留 `BIGINT` 和可空 `resolved_at`。不要主动将列窄化或删除新增列；应用仍保持停写，等待单独的兼容性与恢复决策。已提交的兼容 schema 本身是可保留的前向兼容状态。

### C. 已写入超过 int4 上限的数据

严禁直接执行以下操作：

- `BIGINT → INTEGER`；
- 删除大 sequence；
- 用 `UPDATE` 重写大 sequence 以强行兼容旧 API。

发生严重故障时，保持停写，并使用本次维护窗口生成且已验证的备份恢复到经单独批准的目标环境。恢复备份必然存在恢复点之后的数据损失风险；是否接受该损失、恢复到何处、何时重新开放写入，必须由变更负责人和数据责任人单独决定。不得将恢复操作隐含为本 Runbook 的自动步骤。

## 11. 明确的 Abort / Rollback 条件

出现任一项立即停止进一步操作，保持停写，保存证据并通知变更负责人：

- 备份、SHA-256、文件权限或可读性验证失败；
- preflight 或 schema 再断言与预期不一致；
- 无法证明 Edge/MQTT/API/其他写入者已停止，或存在 MQTT 积压/保留/重放风险；
- lock timeout、statement timeout、DDL 错误、连接中断或提交状态不明；
- telemetry、alarms、inference_results 行数异常；
- 任一 device 的 sequence count/min/max 或 sequence-value signature 异常；
- telemetry 或 inference 唯一约束异常，尤其是 inference 复合约束 OID/定义变化；
- 关键索引、外键或其 OID/定义异常；
- 应用最低兼容性检查失败，或发现旧 API startup compatibility 风险被触发；
- PostgreSQL、宿主磁盘、CPU、内存、连接数或 ECS 资源异常。

## 12. 维护窗口收尾

在所有 post-migration validation 通过后：

1. 将 Go/No-Go checklist、备份 SHA-256、pre/post 输出、OID/定义 diff、停写确认和执行时间写入受控变更记录；
2. 保持 telemetry 写入关闭；
3. 标记状态为 **Database ready for C1 deployment**；
4. 等待后续 C1 Controlled Deployment Plan 的独立授权。

不得在本 Runbook 结束时恢复旧 API、启动 Pi replay、初始化 sequence state、部署 API/Web/Edge、重启生产服务或发送生产遥测。
