# Phase A.3 — C1 Controlled Deployment Plan

## Status and scope

This is a **planning and non-production artifact-verification** document. It
does not authorize a production deployment. The currently accepted production
state is:

- Database migrated and ready for C1 deployment.
- Old API stopped; telemetry writers and Pi replay stopped.
- C1 not deployed; Edge `/state` not initialized.

This plan excludes Phase B/C/D, a model migration or retraining, threshold
changes, production telemetry, old-API restart, and any C2 research changes.
Each production action below requires a separate deployment authorization and a
new maintenance/change record.

## 1. Immutable source and artifact matrix

### Source baseline

| Component | Required source | Evidence |
| --- | --- | --- |
| C1 engineering baseline | `3e99c99179b0f6ccdabb20066e33e5adedc11cc0` | C1 checkpoint |
| API migration fix | `6eb90bbc3d2cb850194d223f66805e0e3c19feec` | Direct child of the C1 baseline; only changes `apps/api/app/database.py` and its PostgreSQL integration test |
| Runtime source to build/deploy | `6eb90bb` | API = C1 plus the idempotent inference-constraint fix; Web and Edge remain C1 |

The Phase A documentation commits after `6eb90bb` do not alter runtime source.
The normal working tree contains uncommitted C2 research material and is not a
permitted image-build source. A detached clean worktree at `6eb90bb` was used
for the following local builds.

### Locally built, non-production images

| Image tag | Target | Local image ID | Build timestamp (UTC) | Dockerfile SHA-256 | Relevant source tree |
| --- | --- | --- | --- | --- | --- |
| `oilwell-ai-api:c1-6eb90bb-amd64` | `linux/amd64` | `sha256:b5ea8ecbd6df7276a94cb8abf357b0ade629d2560792a3703fdff0e6d77d0ae6` | `2026-09-13T08:18:26Z` | `3c76c41a91834761a8e10aa3b513500ac879366806204a094e1b8adbcdae4fad` | `apps/api` tree `86ac87b3a0e91ba38ba27180d8c1a5d4f23bb1fd`; `ml/oilwell_ml` tree `74c7691804328757b35a641af1153cdd31201a43`; knowledge-base tree `aa6eccfd513921c5f65e479f50efd98f96a060d3` |
| `oilwell-ai-web:c1-6eb90bb-amd64` | `linux/amd64` | `sha256:21276fb2ef65ad108ad61a3c4ff937e015b07f303a01663803050254ea9a0753` | local image created `2026-09-12T15:45:04Z`; rebuilt from clean source on 2026-09-13 | `8ffea9ea56039ed566eaf559402e59d8afcb68216a002b7355486e5c23f7e081` | `apps/web` tree `0ff89ab494c2bc70d84bc7617bd1efc9825a5bd9` |
| `oilwell-ai-edge:c1-6eb90bb-arm64` | `linux/arm64` | `sha256:676f40baf3d7d775f52702af96585516afe4a390a58b5ec7bd873fe0cf85badf` | `2026-09-13T08:19:10Z` | `03759798f580f6faa37d65b6176f4f76a6b0bbbb7959dc716780a81b1ede8c66` | `services/edge-agent` tree `c4a60a0569063567e635cd262dac9ad503981a35` |

These are local image IDs, not registry digests. Before deployment, export or
push the exact image, obtain the destination content digest, and record that
digest alongside the image ID above. Do not rebuild from a dirty tree instead.

Local smoke checks passed without production configuration, data, or model
mounts: API imports `app.database` and `app.inference`; Web passes `nginx -t`;
Edge imports `SequenceAllocator`. No service was started as part of those
checks.

## 2. Frozen model-artifact identity

This is not a model release. C1 must retain the present active XGBoost model and
shadow TCN model; active prediction remains the only alarm source. No training,
threshold change, artifact replacement, binary-model switch, or Phase B model
activation is permitted.

| Slot | Declared metadata | Immutable files to verify before API start |
| --- | --- | --- |
| Active | type `xgboost`; metadata has no declared semantic `model_version` or threshold | `xgboost_model.json`: `5ffa7134bbf0b1b5e639aad69173f3898f36131f481bbe1623da6a260a29c606`; `model_metadata.json`: `d8451cf246c95130ec4b43057a26480f54415aec3e24c8a9d1b3ce22fb091b4c` |
| Shadow | type `tcn`, mode `shadow`; metadata has no declared semantic `model_version` | `tcn_model.pt`: `21ce43c87bc9bb96dac5d99daf66f2ba2d5b28b84ad24d721b5870555b4a00ee`; `model_metadata.json`: `bebc2ecf58a57a33cc8f44c675abd21f73d6959f14d0589e6730460b8f7cda51` |

The missing semantic version must be recorded as `unset`, not invented. For
this C1 deployment the listed SHA-256 values are the model release identity.
Before starting C1 API, calculate SHA-256 on the exact production read-only
mounts and require an exact match. A mismatch or unreadable mount is No-Go.

## 3. Production order and shared Go/No-Go rules

The mandatory sequence is:

```text
Record post-A.2 catalog and resources
→ load C1 API image
→ start only C1 API (writers remain stopped)
→ API/catalog/health gate
→ load and start C1 Web
→ Web read-only gate
→ create and validate Edge /state
→ initialize sequence state while writers remain stopped
→ load/start C1 Edge with replay stopped
→ Edge state/heartbeat gate
→ separate approval for the 240-point controlled replay
```

At every stage, no old API restart, no old Edge replay, and no production
telemetry is permitted. Do not run old and C1 API instances as a long-lived
blue/green pair on the 2 vCPU / 2 GiB host.

Any of the following is an immediate No-Go: source/image/model hash mismatch;
unexpected production catalog change; startup migration DDL beyond a no-op;
writer activity; OOM, swap thrashing, repeated restart, or sustained resource
pressure; ambiguous ownership of a `device_id`; or inability to prove the
listed gates. Stop the component introduced by the current stage only; do not
start the old API or old Edge as an automatic rollback.

## 4. C1 API controlled deployment

### Pre-start evidence

Record a fresh, read-only PostgreSQL snapshot after A.2 and before loading C1:

- target column types; all table row counts; per-device count/min/max and
  sequence signature;
- all public constraint/index definitions and OIDs;
- `uq_inference_telemetry_model_mode` definition, constraint OID, and backing
  index OID; and
- host/container memory, CPU, disk, restart count, and PostgreSQL/Mosquitto
  health.

Also record the stopped old API container identity. It remains stopped. Verify
the production model mounts against the hashes in section 2 and verify that
they are mounted read-only.

### Future authorized commands — templates, not authorized by this plan

The operator must substitute the approved immutable image digest and existing
approved environment/volume configuration; do not place credentials in a
change record.

```bash
# Example only — execution requires separate approval.
# Verify the transferred image digest and load it without Compose recreation.
docker image inspect "$C1_API_IMAGE_DIGEST"

# Start only the replacement API container using the reviewed production
# environment, database configuration and read-only model mounts. Preserve
# the existing Docker labels project=infra and service=api for later audits.
# The exact create/run command is subject to pre-execution review.
```

After C1 API starts, collect the same catalog snapshot before and after
lifespan startup. `migrate_schema()` must be a no-op on the Phase A.2 schema:
in particular, `uq_inference_telemetry_model_mode` must retain definition,
constraint OID, and backing-index OID. Any other unexpected schema/catalog
change is Abort; stop C1 API and leave the database migrated.

Then verify only:

- `/api/health` reports database connection, MQTT connection, and both model
  slots ready;
- database telemetry count, per-device max sequence, and active writes remain
  unchanged while Edge remains stopped;
- API logs have no migration error, model-load error, or restart loop; and
- API idle memory is within the pre-approved 2 GiB host budget.

Do not use a replay or fabricated telemetry for this API check.

## 5. C1 Web controlled deployment

Web may start only after every API gate passes. Load the reviewed amd64 image,
replace only Web, and verify the container identity, ready state, proxy path,
and idle memory. Do not alter API, PostgreSQL, Mosquitto, Edge, or model mounts
in this step.

Read-only browser acceptance is:

- dashboard opens through the production proxy;
- wells, history, and alarms read the pre-existing migrated history;
- browser console has no blocking error; and
- API proxy requests succeed without generating telemetry.

If Web fails, stop or roll back only Web to its prior approved image. API and
database stay untouched; writers stay stopped.

## 6. Durable Pi Edge `/state` design

C1 Edge declares the Compose logical named local volume `edge-state`, mounted
read/write at `/state`, with `EDGE_SEQUENCE_FILE=/state/sequence.json`. The
actual Docker runtime volume name may be project-prefixed; it must be resolved
and recorded with `docker volume inspect` before use. It is a Docker named
volume, not a container filesystem path and not a bind mount to replay data.

Before first C1 Edge start, the future deployment operator must verify:

- `docker volume inspect "$EDGE_STATE_RUNTIME_VOLUME"` reports the resolved
  local named volume and its persistent mountpoint on the Pi;
- the Edge container mounts exactly `edge-state:/state` read/write, and
  `/data` remains read-only;
- the container runtime user can atomically create and replace the state file,
  fsync its containing directory, and produces the recorded approved file mode
  (not writable by unprivileged users); and
- image update/recreate preserves the named volume. Never run a volume-removal
  command (`docker volume rm`, `compose down -v`, or equivalent) in this path.

The normal Docker volume survives container recreation and Pi reboot as long as
the Docker data directory is retained. The mount, its ownership/mode, and the
single assigned `EDGE_DEVICE_ID` must be recorded in the deployment record.
There must be exactly one telemetry writer for that device ID; do not run old
and C1 Edge together.

## 7. Sequence-state initialization while all writers are stopped

This is a future authorized operation, not part of this planning phase.

1. Reconfirm API/Edge/other writers are stopped and the broker has no replay
   path for the device.
2. Query production at that time: `SELECT max(t.sequence) FROM public.telemetry
   AS t WHERE t.device_id = 'edge-pi-01';` and record the returned value as
   `M`. Never reuse a historical number.
3. Inspect `/state/sequence.json`. If it is absent, set `U=0`. If present,
   require JSON `{"schema":1,"reserved_until":<integer>}`; malformed state is
   No-Go and must not be reset or overwritten.
4. Atomically create/update the state with `reserved_until=max(M,U)`, schema 1,
   owner/mode appropriate for the Edge runtime, file fsync, rename, and parent
   directory fsync. Re-read and validate the file.
5. Before Edge starts, require `reserved_until >= M`, `reserved_until <
   9007199254740991`, and one writer only. On C1 Edge startup,
   `SequenceAllocator` uses `max(current_microsecond_time, reserved_until)` and
   immediately persists the next lease; verify that lease's upper bound is
   greater than `M`, below the JavaScript safe-integer limit, and non-overlapping
   with database history.

No telemetry is sent to test this initialization. Do not lower
`reserved_until`, restore an older state snapshot, or delete `/state` after it
has advanced.

## 8. C1 Edge deployment gate

Only after database, C1 API, Web (if in scope), durable `/state`, initialized
state, and sequence-range validation pass may C1 Edge start. Set replay
autostart off and retain the STOP state. Confirm:

- arm64 image identity is the approved digest;
- container is running and `edge-state` is mounted at `/state`;
- a status heartbeat is ONLINE with a readable sequence state and explicit
  selected-instance status;
- replay reports stopped/not replaying; and
- no telemetry rows are inserted.

If Edge fails, stop C1 Edge only. Preserve `/state` and its highest
`reserved_until`; do not start old Edge or replay.

## 9. Separate real-machine Phase A replay acceptance

After a separate approval, use exactly one documented 3W instance for a
240-point / 1× controlled replay. The operator must record the actual file,
derive/verify `well_id` from that file and configuration, and not assume
`WELL-00014`. The new sequence range must be strictly after the database MAX
read at initialization.

Acceptance traces the full path:

```text
Edge → MQTT → API → PostgreSQL → window → inference → WebSocket → Vue
```

Record 240 source samples, newly inserted telemetry count, unique monotonic
sequences, source timestamps, all seven variables, well ID, inference-window
count and latency, WebSocket delivery, and UI rendering. With a 180-point
window and 10-point step, report the actual inference count produced by this
instance rather than claiming that inference merely ran.

Alarm acceptance remains separate. If the unchanged active model produces a
real anomaly, validate its real alarm lifecycle. Otherwise record:
`engineering inference path passed; real-model alarm trigger not observed`.
Do not change thresholds, fabricate predictions, treat event labels as model
predictions, or keep choosing instances until an alarm appears. Local fixed
prediction state-machine tests are engineering evidence only.

## 10. Resource budget and rollback boundaries

The production ECS class is 2 vCPU / 2 GiB. Before and after each component,
record available host memory plus API, Web, PostgreSQL, Mosquitto, and total
container memory/CPU/restart count. The current compose limits are API 512 MiB,
Web 128 MiB, PostgreSQL 512 MiB, and Mosquitto 128 MiB; they are ceilings, not
an approval to exhaust the host. OOM, swap/thrashing, repeated restart, or
sustained exhaustion is Abort and requires stopping the newly introduced C1
component.

| Failure stage | Safe rollback boundary |
| --- | --- |
| C1 API startup/catalog/health | Stop C1 API; keep migrated database and writers stopped. Never automatically start old API because its startup has historical DDL risk. |
| C1 Web | Stop or return only Web to its prior approved image; leave API/database unchanged. |
| C1 Edge or state validation | Stop C1 Edge; retain the named `/state` volume and never lower `reserved_until`; do not start old Edge/replay. |

## 11. Deployment Go/No-Go checklist

- [ ] New maintenance ID and fresh production evidence created; no prior-window evidence reused.
- [ ] Source commit is exactly `6eb90bb`; local C2 working-tree content was not used.
- [ ] Destination image digests match the reviewed source/image matrix and target architecture.
- [ ] Production active/shadow artifact file and metadata SHA-256 values exactly match section 2; mounts are read-only.
- [ ] Database post-A.2 catalog/data baseline is recorded and unchanged before C1 API start.
- [ ] Old API remains stopped; all telemetry writers, Pi replay, and broker replay paths are stopped/cleared.
- [ ] C1 API startup catalog diff is no-op; health, MQTT, models, database, and no-write checks pass.
- [ ] C1 Web is verified read-only after API health passes.
- [ ] `edge-state` is persistent, writable by Edge, protected from deletion, and assigned to one device writer.
- [ ] Sequence state is initialized from fresh `M` and validated without telemetry.
- [ ] C1 Edge heartbeat/state/replay-stopped gate passes before any replay approval.
- [ ] Resource observations remain within the 2 vCPU / 2 GiB operational budget.

Until every applicable item is checked under a separately authorized deployment
window, the required status remains **Database ready for C1 deployment** — not
C1 deployed, not Edge ready, and not Phase A accepted.
