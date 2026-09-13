# Phase A.1 — Production Compatibility Audit

## 1. 结论

**不兼容，停止在审计阶段：不能直接部署 C1 Edge/API，不能进入执行性质的 C1 部署准备。需要先单独审批数据库兼容迁移和 sequence/state 初始化方案。** 本轮没有执行迁移、部署、重启、回放或任何生产数据写入。

| 项目 | 本轮结论 |
|---|---|
| telemetry.sequence | 生产为 INTEGER / int4；C1 为微秒级整数，必须升级为 BIGINT |
| alarms.resolved_at | 生产缺列；C1 ORM 与恢复逻辑需要该列，必须兼容补充 |
| 遥测去重 | 实际存在 UNIQUE(device_id, sequence) 及唯一 B-tree 索引 |
| inference_results | model_type/model_mode 已存在，UNIQUE(telemetry_id, model_mode) 已存在 |
| Pi /state | 无 /state 挂载、目录或 sequence 文件；不能提供 C1 持久化保证 |
| 当前计数与数据库 | Agent 当前计数落后于数据库最大值，存在已证实的历史键重叠 |
| C1 制品契约 | 不训练、不替换模型；本轮仅分析 C1 代码，不实例化 SequenceAllocator |
| 是否生成受控部署计划 | 本轮不生成可执行部署计划；先提出独立迁移提案并等待确认 |

## 2. 证据范围与只读约束

- ECS 采集：`2026-09-13T05:36:44.419033+00:00`。
- Pi 采集：`2026-09-13T05:37:39.763273+00:00`。
- 生产计数查询：`2026-09-13T05:38:50.517464+00:00`。时间均为 UTC；北京时间加 8 小时。
- 比较目标为 C1 `3e99c99179b0f6ccdabb20066e33e5adedc11cc0`，审计工作树 `codex/phase-a-verification`。

ECS/Pi 使用已有 SSH 身份；只读执行 docker inspect/image inspect、docker stats、文件哈希、HTTP GET 和 PostgreSQL SELECT。psql 使用 `-X`、ON_ERROR_STOP、会话级 `default_transaction_read_only=on`，SQL 显式 `BEGIN READ ONLY`；statement_timeout=8s、lock_timeout=1s。数据库返回 transaction_read_only=on。未导入/启动 API 主模块，未通过新 API 隐式迁移。

报告依据本轮新采集 JSON 与当前 C1 源码；不引用旧截图作为现状。底层读取全部生产七表列定义、约束和索引；报告列出关键结果。对 C1 自动比对覆盖列存在性、SQL 基础类型与声明索引名称，不冒充 varchar 长度、全部默认值、权限及触发器的完整等价证明。

## 3. ECS 当前发布身份与资源

| 容器 / Compose 服务 | 当前 image ID（SHA-256） | 启动时间 UTC | 状态 / 重启次数 |
|---|---|---|---|
| `/infra-api-1` / `api` | `sha256:19c136ecf108d22e24c5f86e6a94585eeac60f78d0b23fbba0ffbe7a43e37078` | `2026-09-12T12:27:05.865139669Z` | running / 0 |
| `/infra-web-1` / `web` | `sha256:c5f8956ea9d4f7d99b79f31d77828e41554b36adb309260122108fbaed96996c` | `2026-09-12T12:37:12.873574219Z` | running / 0 |
| `/infra-mosquitto-1` / `mosquitto` | `sha256:4725ea7590a578122675b1fdd242b94e5034885cfd0806045b25d700f5498ef5` | `2026-09-12T11:17:28.291088119Z` | running / 0 |
| `/infra-postgres-1` / `postgres` | `sha256:75f5a96988cdf694a215073c3e9c001b706b371e2f94df3967f2efdec2787f6b` | `2026-09-12T11:17:28.261813533Z` | running / 0 |

这些值是 Docker image ID，即配置内容摘要。ECS 四个镜像的 RepoDigests 均为空，**不能将其冒充可从 registry 拉取的 manifest digest**；未来回退需保存本地镜像或可验证镜像归档。Compose project 为 infra，当前四个服务均运行。

API/Web 容器及镜像未暴露检查范围内的 release/commit 标签；也没有 GIT_COMMIT、COMMIT_SHA、RELEASE_VERSION、APP_VERSION、BUILD_SHA 环境标识。完整构建 commit **尚不能严格确定**。API 五个源文件（main/database/models/inference/realtime）本轮 SHA-256 与 Git `34e69ad` 内容一致、与 C1 不同；这支持“旧代码”，不能等价为完整镜像 commit 证明。

| API 运行健康 | 本轮值 |
|---|---|
| `status` | `ok` |
| `mqtt_connected` | `True` |
| `window_seconds` | `180` |
| `inference_status` | `ready` |
| `inference_error` | `None` |
| active 模型 | `xgb-20260912T082447Z` / `ready` / `xgboost` |
| shadow 模型 | `tcn-20260912T084752Z` / `ready` / `tcn` |

保持现有模型制品原样。模型 ready 是运行时状态，不代表 C1 已部署或实机验收通过。当前 API 的模型挂载为只读；详细挂载与制品哈希见原始证据。

| 服务 | 本轮内存占用 / 限制 | CPU | PIDs |
|---|---|---|---|
| `infra-api-1` | 242.1MiB / 512MiB | 0.14% | 9 |
| `infra-web-1` | 3.859MiB / 128MiB | 0.00% | 3 |
| `infra-mosquitto-1` | 3.785MiB / 128MiB | 0.02% | 1 |
| `infra-postgres-1` | 32.52MiB / 512MiB | 0.01% | 8 |

宿主机 2 CPU；可见总内存 1,758,584,832 B（约 1.64 GiB），available 899,391,488 B（约 858 MiB），无 Swap；根盘使用 57%，可用 17,281,294,336 B。这是瞬时读数，不是压测、峰值预算或蓝绿部署余量证明。

## 4. Raspberry Pi 当前发布身份

- 容器：`/oilwell-ai-edge-edge-agent-1`。
- image ID：`sha256:dc58637fe4096d01ff961e1432567bf553fe98a4b2bc163e8b747ba7aaddfe0f`。
- Docker 返回 RepoDigest：`oilwell-ai-edge@sha256:dc58637fe4096d01ff961e1432567bf553fe98a4b2bc163e8b747ba7aaddfe0f`。只记录实际返回值，不假设 registry 可访问。
- 启动时间：`2026-09-12T12:14:05.210189537Z`；状态 `running`；重启次数 0。
- 无检查范围内的 release/version 标签。Agent 源码各文件 SHA-256 已采集，不能仅凭 latest 标签确定版本。

- selected instance：`WELL-00001_20170201010207.parquet`。
- replay state：`ONLINE`（未回放）。
- speed：20×。
- 当前 sequence：`1789215557`。
- 最后心跳：`2026-09-13T05:38:41.918105Z`；相对查询时间约 9 秒，符合已配置 10 秒心跳周期，当前在线。

源码本轮确认 `self.sequence = int(time.time())`，每发送一次执行 `self.sequence += 1`；payload 使用 `self.settings.well_id`，当前配置固定为 WELL-00014。不会随选中的 WELL-00001 文件自动切换井 ID。

实际挂载只有 `/data` 的只读 bind mount。没有 `/state` 卷、没有 EDGE_SEQUENCE_FILE 环境配置，`/state` 目录和 `/state/sequence.json` 均不存在。当前策略不是持久化 lease；本轮未创建目录/卷/文件、未重启、未更换实例。

## 5. PostgreSQL 实际 schema 与序列证据

数据库 `oilwell`，schema `public`，PostgreSQL `16.15`。

### 5.1 字段与约束

| 项目 | 生产实际 | C1 需要 | 判断 |
|---|---|---|---|
| telemetry.sequence | INTEGER / int4，NOT NULL，无列默认值 | BIGINT / int8，NOT NULL | 不兼容 |
| 遥测唯一键 | uq_telemetry_device_sequence：UNIQUE(device_id, sequence)，validated=true | 同名同列唯一键 | 兼容 |
| 遥测索引 | 主键、device_id、timestamp、well_id、上述复合唯一索引 | 相应索引 | 本次比对一致 |
| inference_results.model_type | character varying，字段存在 | 字段存在 | 基础类型兼容 |
| inference_results.model_mode | character varying，字段存在 | 字段存在 | 基础类型兼容 |
| 推理唯一键 | uq_inference_telemetry_model_mode：UNIQUE(telemetry_id, model_mode)，validated=true | 相同 | 兼容 |
| 旧 uq_inference_telemetry | 当前不存在 | 不应保留单 telemetry 唯一限制 | 兼容 |
| alarms.resolved_at | 不存在 | 可空 TIMESTAMPTZ | 不兼容 |
| diagnostic_records.evidence_status/degradation_reasons | character varying / JSONB，已存在 | 对应审计列 | 基础类型兼容 |

C1 所声明的索引名在生产均能找到；除 sequence 类型和 resolved_at 缺列外，本次列存在性/基础类型比较未发现其他差异。完整实际列、默认值、NULL 约束、外键、索引 DDL 都保存在 ecs-current.json。C1 启动迁移仍包含删除后重建推理唯一约束的 DDL；即使约束已经兼容，也不能把启动 C1 API 当成无 schema 副作用的健康检查。

关键真实索引定义（读取结果，不是执行）：
```sql
CREATE UNIQUE INDEX uq_telemetry_device_sequence
ON public.telemetry USING btree (device_id, sequence);
CREATE UNIQUE INDEX uq_inference_telemetry_model_mode
ON public.inference_results USING btree (telemetry_id, model_mode);
```

### 5.2 当前 Edge 的计数

- device_id：`edge-pi-01`。
- 生产行数：3817；distinct sequence：3817。
- 最小 sequence：`1`；**最大 sequence：`1789216640`**。
- Agent 当前值：`1789215557`，比数据库最大值低 **1083**。
- 相同 (device_id, sequence) 重复组：0。唯一约束阻止重复行入库，不能因此认为发送端没有碰撞。

- 按插入主键 id 倒序最近 20 行：sequence `1789216621–1789216640`，均归 WELL-00014。源时间 `2016-03-04T16:23:17+00:00` 至 `2016-03-04T16:23:36+00:00`。按 id 排序仅近似插入先后；表没有接收时刻列，不能将源时间当成最近入库时间。

最近 5 行：

| id | sequence | well_id | 源时间 |
|---:|---:|---|---|
| 6983 | 1789216640 | WELL-00014 | 2016-03-04T16:23:36+00:00 |
| 6982 | 1789216639 | WELL-00014 | 2016-03-04T16:23:35+00:00 |
| 6981 | 1789216638 | WELL-00014 | 2016-03-04T16:23:34+00:00 |
| 6980 | 1789216637 | WELL-00014 | 2016-03-04T16:23:33+00:00 |
| 6979 | 1789216636 | WELL-00014 | 2016-03-04T16:23:32+00:00 |

本轮再次用生产 SQL 查询区间 1789215247–1789215557：共 311 行、归属 WELL-00014、源时间为 2016-03-04T16:00:23Z 至 16:05:33Z。这些都是存量键。当前计数附近及更高值也已存在；旧 Agent 若继续递增将重复已有键。该结论来自本轮只读查询，不依赖旧截图，也没有试发消息。

当前 telemetry 堆 581,632 B、索引 581,632 B、合计 1,204,224 B。表不大，但不代表 ALTER 无锁等待或无需备份。

## 6. C1 sequence compatibility：逐项回答

### 6.1 新初始值如何产生

C1 `SequenceAllocator` 读取 schema=1 的 JSON 中 reserved_until；不存在文件则 previous=0。令 T=`time.time_ns() // 1000`，U=已保存 reserved_until：

```text
value = max(T, U)
reserved_until = value + 10_000  # 先原子写入并 fsync
第一个发送值 = value + 1
```

本轮 Pi 时钟 T=`1789277860386410`；若按该瞬时读数且无 state，首值为 `1789277860386411`。这是计算示例，未创建分配器或发送消息；实际启动须重新采样。

### 6.2 如何保证第一次启动严格高于生产最大值

当前 T 远大于 M=`1789216640`，所以时间条件在本轮读数上满足。但是 C1 **不会查询生产 MAX(sequence)**，不能单靠代码承诺数据库高水位安全。未来部署门禁应停止同 device_id 的所有写入者，再读取新 M；保留 existing U，原子初始化 state 的 reserved_until 至少为 max(M,U)，不得覆盖为更小值。构造器随后确保首值 max(T,U,M)+1 > M；启动前还需检查 max(T,U,M)+10,000 不超过安全上限。

### 6.3 容器重建与 Pi 重启

有稳定、可写且保留的同一 Docker named volume 时，保存的是已预留上界；重启会跳过未消费租约，保持单调但不保证连续无缺口。文件写入使用临时文件、flush/fsync、原子替换及父目录 fsync。前提是卷不删除、不更换 Compose project/volume identity、无旧快照回滚且只有一个写入者；代码没有跨进程租约锁，不能让同一 device_id 的两个 Agent 并发。当前 Pi 完全没有该卷，因此当前配置不满足这一保证。

### 6.4 数值上限是否适配

INTEGER 最大 2,147,483,647，无法保存约 1.789×10^15 的 C1 初值；BIGINT 最大 9,223,372,036,854,775,807，可以保存。C1 更严格限制预留上界 ≤9,007,199,254,740,991，以兼容 JavaScript 安全整数。达到上限时 `_reserve()` 抛错，不继续发号。**生产 int4 不兼容，必须先迁移。**

### 6.5 state 丢失时的保护

存在文件但 JSON 解析失败、schema 不符或 reserved_until 不是 int 时会抛错；文件写入失败也会阻止成功预留。**文件丢失与首次安装无法区分：代码会退回当前微秒时间，不会自动拒绝启动，也不会与数据库比对。** 在时钟倒退、卷回滚或多写入者情形仍可能碰撞。未来部署运维必须把“已部署设备 state 缺失”设为人工停止条件，先核对 DB 高水位再恢复，不直接删 state 重启。此处是运维门禁建议，未新增代码保护。

### 6.6 是否需要部署前初始化 lease/state

需要明确的初始化与核验步骤；建议对当前无 state 的设备预置 `{ "schema": 1, "reserved_until": M }`，M 必须在排除并发写入后重查，不能把本报告常数直接作为未来启动种子。若已有文件，则只向上保留 max(existing U,M)。初始化应原子写入、fsync、校验权限及挂载身份；本轮未执行。

### 6.7 是否需要数据库迁移

需要：telemetry.sequence→BIGINT，alarms.resolved_at→新增可空 TIMESTAMPTZ。当前推理复合唯一约束与字段已经具备，不应因本次兼容迁移主动重复改造；但后续 C1 启动自带约束重建仍需纳入部署变更窗口说明。

## 7. 独立下一步提案：数据库兼容迁移（未执行，等待确认）

这是因审计发现不兼容而提出的独立下一阶段，不是本次执行内容，也不是 C1 Controlled Deployment Plan。不得直接复制 SQL 到生产执行。

### 修改与 SQL

只改两个 schema 项，不改数据标签、模型、well_id、历史 sequence 值或已有唯一性语义。先在隔离恢复库验证，再在另行批准的维护窗口执行：

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

执行前必须再次断言当前是 int4 且 resolved_at 缺失；如果 schema 已变化，停止重审，不能盲目套用。任何语句失败应回滚整个事务。

### 影响、备份与验证

- int4→int8 可能重写 telemetry 并重建相关索引，取得 ACCESS EXCLUSIVE 锁；会阻塞入库与相关查询。小表不等于零停顿。禁止通过扩大超时或无限重试掩盖锁竞争。
- 维护窗口须单独批准暂停写入方及其恢复顺序；API/MQTT 的积压或重连风险另行验证，本审计不暂停任何生产进程。
- 执行前建立受限访问的 PostgreSQL custom-format 全库备份与 schema-only 备份，记录哈希；在隔离 PostgreSQL 16 恢复演练，核对约束、行数及每设备 max sequence。备份包含生产数据，不提交 Git。
- 正式操作前后比较 telemetry/alarms 行数、每设备 min/max/count、唯一约束、索引、外键、sequence 类型、resolved_at 类型/可空性；保持数值和历史记录不变。
- 检查旧 API 可正常读写 int8 范围内的原小整数，以及新 C1 的大整数兼容性；大整数用隔离恢复库验证，不试发生产遥测。数据库验证通过也不自动放行部署。

### 回滚

- 事务未提交或执行失败：ROLLBACK，不留下部分 schema。
- 已提交但应用需要回退：优先保留向后兼容的 BIGINT 与可空新增列，回到旧镜像；不要立即窄化字段或删除列。旧 Edge 的碰撞问题仍存在，回退后也不能无条件恢复回放。
- 一旦写入大于 INTEGER 上限的值，禁止直接改回 int4。若发生必须恢复数据库的事故，应另行停写并恢复经过演练的备份，明确备份后数据的恢复点损失与补偿方案，不能 UPDATE/DELETE 大值来让窄化成功。
- 回滚条件：备份恢复演练失败、锁超时、DDL 错误、行数/高水位/约束异常、旧应用兼容检查失败；对应停止执行或事务回滚，不继续部署。

## 8. 本轮操作与证据清单

只新增本审计文档和本地忽略证据；不处理 C2、不改模型、不开展 Phase B/C/D。未执行报告中的任何迁移 SQL，未创建或初始化生产 state，未变更环境变量、实例、速度或容器配置。

| 证据文件（忽略目录 compatibility-20260913） | SHA-256 |
|---|---|
| `ecs-current.json` | `e794157116b92d4158890ae76e1d8b33cce4df8b29b17f7fa747e263f597e61d` |
| `pi-current.json` | `f506db29b5b6eddc91484d92182ea2d794bee92d229dd5828e4ab28cc882d233` |
| `database-current.json` | `a145525f7a86a2adacbeff7cb9d6a4b746b64fc08f335c1560a867fa9bc8db4b` |
| `c1-schema-comparison.json` | `28d4e3618f0f1de874dd2758c7bf1b374b473067da463cc7fcb880e4a8ca7087` |
| `ecs_audit.py` | `fd3af0702861bee3b19def4b5b289b423460d601fccbf5a765dd8cd650de03ab` |
| `pi_audit.py` | `4a21e7da25b2bcdabd95784208aff760d4812f7f334c81ce87d02df5bf1f4082` |
| `db_sequence_audit.py` | `5b81bd610235fcc67e7c792d9721333ee3e58ab714fbb15ae9775e5d3931bb6b` |

原始证据不随文档提交，且不得把 SSH 密钥路径、凭据或原始传感器数据复制进报告。IP/身份配置只用于现有连接，报告不公开。
