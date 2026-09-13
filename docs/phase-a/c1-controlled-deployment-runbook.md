# Phase A.3.1 — C1 Controlled Deployment Runbook

## 0. Authority, fixed state, and stop boundary

This Runbook is prepared and non-production validated, but **is not deployment
authority**. A future execution needs a new maintenance ID and explicit
approval. Until then, production remains: database migrated; old API stopped;
the old Edge container is observed running; C1 absent; Edge `/state` remains
uninitialized. Do not infer its replay or writer state from that observation.

Stop after this fixed sequence; do not enter 240-point replay:

```text
Artifact verification → fresh ECS/Pi target identity
→ old Edge replay-stopped verification → graceful retirement of old Edge
→ broker/no-write verification → C1 API deployment → API catalog/no-write gate
→ C1 Web deployment → Web read-only gate → canonical Edge state volume
→ fresh DB MAX(sequence) → locked state initialization
→ C1 Edge deployment with replay stopped → Edge heartbeat/state/no-write gate
```

Never use Compose in this procedure: current production Compose interpolation
is not an approved control path. Never start old API or old Edge as rollback.
All evidence paths below are protected, non-Git paths under
`$MAINT_EVIDENCE_DIR`; no passwords, private keys, tokens, or full connection
strings may be copied into the change record.

### Unified fail-closed graceful stop

For API, Web, and Edge, first record the exact container ID, image ID, PID and
`.Config.StopSignal`. Empty StopSignal means `SIGTERM`; `SIGKILL`, `KILL`, or
`9` is No-Go. Use the fixed ID only: send `docker kill --signal
"$STOP_SIGNAL" "$CONTAINER_ID"`, then inspect once per second for at most 20
seconds. Success requires `running=false` and `status=exited`. Signal failure
or timeout is Abort: do not send a second signal, SIGKILL, `docker stop`,
restart, remove, or Compose command. This procedure replaces every stop below.

```bash
STOP_SIGNAL="$(docker inspect --format '{{with index .Config "StopSignal"}}{{.}}{{end}}' "$CONTAINER_ID")"
STOP_SIGNAL="${STOP_SIGNAL:-SIGTERM}"
case "$STOP_SIGNAL" in SIGKILL|KILL|9) exit 1;; esac
docker kill --signal "$STOP_SIGNAL" "$CONTAINER_ID"
for elapsed in $(seq 1 20); do sleep 1; state="$(docker inspect --format '{{.State.Status}}|{{.State.Running}}' "$CONTAINER_ID")"; [ "$state" = 'exited|false' ] && break; done
[ "${state:-}" = 'exited|false' ] || exit 1
```

## 1. Fixed source and image identity chain

API runtime source is `6eb90bbc3d2cb850194d223f66805e0e3c19feec`; Web is the
audited C1/`6eb90bb` Web artifact; Edge runtime source is `1d13bc8` (`fix:
enforce single writer ownership for edge state`). The Edge-only commit adds
ownership protection and does not alter API/Web, ML models, lease semantics,
or Phase B/C/D. Do not build from the ordinary workspace containing C2 work.

| Component | Platform | source image ID |
| --- | --- | --- |
| API | `linux/amd64` | `sha256:b5ea8ecbd6df7276a94cb8abf357b0ade629d2560792a3703fdff0e6d77d0ae6` |
| Web | `linux/amd64` | `sha256:21276fb2ef65ad108ad61a3c4ff937e015b07f303a01663803050254ea9a0753` |
| Edge | `linux/arm64` | `sha256:f0284dee673fc229145e9f8b5b68000ed7e7993a6ce361493323be3d136375bc` |

The prior Edge image `sha256:676f40baf3d7d775f52702af96585516afe4a390a58b5ec7bd873fe0cf85badf` is **superseded and not deployable**. The candidate Edge Dockerfile SHA-256 is `03759798f580f6faa37d65b6176f4f76a6b0bbbb7959dc716780a81b1ede8c66`; Edge source tree is `85f7a374615b8c4cea63abc17f36ec7ee1e0cbb7`. Before deployment, establish its image-to-archive SHA-256-to-transferred archive-to-destination image-ID chain.

Use archive transfer, not a tag-only registry pull. On the isolated builder,
the API archive was successfully saved/loaded, measured 1.2 GiB, and had
SHA-256 `299874889331644433478cc2209b887140993eacb593f1358474fa8e8eac5837`;
the loaded image retained the approved API ID and `amd64` architecture.

### Future authorized artifact commands

Run from the clean release worktree or its approved builder host only. Transfer
the three archives over the approved authenticated channel; record transfer
receipt and archive SHA-256 in protected evidence.

```bash
set -o errexit -o nounset -o pipefail
docker save -o "$API_ARCHIVE" "$API_SOURCE_IMAGE_ID"
docker save -o "$WEB_ARCHIVE" "$WEB_SOURCE_IMAGE_ID"
docker save -o "$EDGE_ARCHIVE" "$EDGE_SOURCE_IMAGE_ID"
sha256sum "$API_ARCHIVE" "$WEB_ARCHIVE" "$EDGE_ARCHIVE" | tee "$MAINT_EVIDENCE_DIR/archive-sha256.txt"

# On the target: verify received bytes before loading; target must be correct
# architecture (amd64 for ECS, arm64 for Pi).
sha256sum -c "$MAINT_EVIDENCE_DIR/archive-sha256.txt"
docker load -i "$API_ARCHIVE"
docker image inspect --format '{{.Id}}|{{.Os}}/{{.Architecture}}' "$API_SOURCE_IMAGE_ID"
```

Repeat the last two lines for Web/Edge and compare the resulting image ID plus
OS/architecture to the table. A tag mismatch, archive hash failure, or any
different target image ID is No-Go. Do not retag an unverified image as proof.

## 2. Fresh runtime capture and common preflight

At the start of the authorized window, capture the stopped old API and current
Web using `docker inspect`, emitting environment **names only**. The current
ECS evidence establishes: `infra-api-1` is exited, has labels
`project=infra/service=api`, port `127.0.0.1:8000`, network `infra_default`,
restart `unless-stopped`, 512 MiB memory limit, working dir `/app`, and three
read-only model bind mounts. Web has labels `infra/web`, port
`127.0.0.1:8085`, `infra_default`, `unless-stopped`, and a 128 MiB limit.

Before Edge work, load the protected, Git-ignored production target record at
`docs/.local/targets/production-edge.json`. Connect only to that record's
fixed approved endpoint; never select a host from an address scan, historical
log, or hostname similarity, and do not try a fallback host. Read-only verify
the record's exact machine-id hash, hostname, architecture, Docker
availability, exactly one old Edge container, and `edge-pi-01` device ID.
Any mismatch is No-Go. A missing `verified_wireguard_endpoint` does not permit
inventing one: use only the record's verified endpoint and document the
observed topology.

After identity verification, run the same sanitized capture on the registered
Pi host for the old Edge container. Its host identity, logical/runtime volume
name, environment names, `/data` mount, UID/GID, MQTT endpoint parameters,
and device label must be obtained afresh. Without a uniquely identified Pi
target and capture, Edge is No-Go.

```bash
# Approved read-only capture template; do not print environment values.
docker inspect "$CONTAINER_ID" > "$MAINT_EVIDENCE_DIR/runtime-raw.json"
docker inspect --format '{{.Id}}|{{.Name}}|{{.Image}}|{{.Config.Image}}|{{.State.Status}}|{{.State.Pid}}|{{.State.StartedAt}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{.Path}}|{{json .Args}}|{{json .Config.Entrypoint}}|{{json .HostConfig.PortBindings}}|{{json .NetworkSettings.Networks}}|{{json .Mounts}}|{{json .HostConfig.RestartPolicy}}|{{.HostConfig.Memory}}|{{.HostConfig.NanoCpus}}|{{.Config.User}}|{{.Config.WorkingDir}}|{{with index .Config "StopSignal"}}{{.}}{{end}}' "$CONTAINER_ID" > "$MAINT_EVIDENCE_DIR/runtime-sanitized.txt"
docker inspect --format '{{range .Config.Env}}{{println (index (split . "=") 0)}}{{end}}' "$CONTAINER_ID" | sort -u > "$MAINT_EVIDENCE_DIR/environment-names.txt"
```

Use the observed mounts/networks/ports/environment names; never reconstruct
them from memory. Also record host available memory, each container's memory
and CPU, total container use, and restart counts. OOM, swap/thrashing, repeated
restart, or resource exhaustion is No-Go.

Create C1 env files only from the maintenance-window-approved old container:
`docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}'
"$OLD_CONTAINER_ID" > "$API_ENV_FILE"` (and likewise Edge), with `umask 077`
and mode `0600`. Do not print values. Record only sorted variable names and the
env-file SHA-256 publicly. Reject unknown names; inject only documented C1
state variables separately. Inability to safely extract the approved env is
No-Go.

## 3. Old Edge retirement gate

This gate is mandatory **before C1 API startup**.

### Fresh Pi target identity

For every deployment maintenance window, connect only to the protected target
record's `production-edge-pi-01` endpoint, currently
`dowdah@192.168.50.200`. Revalidate the recorded host-key fingerprint,
hostname, machine-id SHA-256, `aarch64`/`arm64` architecture, Docker
availability, exactly one old Edge candidate, and
`EDGE_DEVICE_ID=edge-pi-01`. Any mismatch, missing target record, zero/multiple
candidates, or device-ID mismatch is No-Go. Do not try another endpoint.

The Pi has no direct WireGuard IP. ECS `wg0` and router `wgc5` are transit
only, never a Pi SSH endpoint. A future jump transport to the same registered
LAN endpoint must revalidate the same host key, machine-id, hostname,
architecture, and device ID; a transport change cannot change target identity.
Any new direct Pi endpoint requires separate user approval and registration.

### Capture and prove no-write state

Using the fixed old-Edge container ID, capture and record its container/image
IDs, PID, optional StopSignal, project/service labels, device ID, state,
restart policy, mounts, and network with the sanitized capture template above.
Read and record the current replay state and selected instance through the
approved existing Edge status/control path; do not infer either from a
container name or image tag. Confirm it is the previously audited old Edge.

Before stopping it, prove replay is not running and take repeated approved
database/broker observations showing telemetry count and each-device maximum
sequence stable. If replay is running, use the already approved Edge `STOP`
control path and wait for its confirmation. If STOP cannot be confirmed, broker
drain cannot be proven, or the stable observations change, this is No-Go.

### Fail-closed retirement

Fix and record the old Edge container ID, image ID, PID, and StopSignal, then
execute the unified fail-closed graceful-stop procedure in Section 0. Empty
StopSignal means `SIGTERM`; `SIGKILL` is No-Go. Only an explicit normal signal
to that fixed ID is permitted. Poll once per second for at most 20 seconds;
only `running=false` and `status=exited` succeeds. A signal failure or timeout
is Abort. Do not send SIGKILL or a second signal, and do not use `docker stop`,
restart, remove, or Compose.

After success, retain the exited old container and its historical data mount
for audit. Do not start it, restore its heartbeat, restart replay, delete data,
or remove other historical assets. Recheck runtime writer count equals zero,
the broker has no retained/backlogged telemetry from this Edge, and telemetry
count/max(sequence) remains stable. Only then may C1 API deployment begin.

## 4. API deployment and catalog gate

### Preconditions

1. Confirm exactly one label-selected old API exists and is `exited`; do not
   start it. Confirm no currently running container has labels
   `com.docker.compose.project=infra` and `com.docker.compose.service=api`.
2. Confirm Phase A.2 state: `telemetry.sequence` is `int8`,
   `alarms.resolved_at` is nullable `timestamptz`, and take a full public
   constraint/index/OID, row-count, per-device max, and active-write baseline.
3. Hash the exact production read-only model mounts. Require the active model
   and metadata hashes `5ffa7134bbf0b1b5e639aad69173f3898f36131f481bbe1623da6a260a29c606` /
   `d8451cf246c95130ec4b43057a26480f54415aec3e24c8a9d1b3ce22fb091b4c`,
   and shadow model/metadata hashes `21ce43c87bc9bb96dac5d99daf66f2ba2d5b28b84ad24d721b5870555b4a00ee` /
   `bebc2ecf58a57a33cc8f44c675abd21f73d6959f14d0589e6730460b8f7cda51`.

### Future authorized API command

`$API_ENV_FILE`, `$API_MODEL_*_SOURCE`, `$API_NETWORK`, and `$API_PORT` are
values captured in this same window; the command does not parse Compose.

```bash
set -o errexit -o nounset -o pipefail
docker run -d --name infra-api-c1 \
  --label com.docker.compose.project=infra \
  --label com.docker.compose.service=api \
  --restart=no --memory 512m --network "$API_NETWORK" \
  -p "127.0.0.1:${API_PORT}:8000" --env-file "$API_ENV_FILE" \
  -v "$API_MODEL_CURRENT_SOURCE:/models/current:ro" \
  -v "$API_MODEL_SHADOW_SOURCE:/models/shadow:ro" \
  -v "$API_MODEL_EXPLANATIONS_SOURCE:/models/explanations:ro" \
  "$API_SOURCE_IMAGE_ID"
```

Verify exactly one *running* `infra/api` label selection and capture its ID,
image ID, labels, mounts, network, port, restart policy, and memory limit.

Take the catalog snapshot immediately before and after API startup. Require
identical definitions/OIDs for all unrelated catalog objects, and identical
definition, constraint OID, and backing-index OID for
`uq_inference_telemetry_model_mode`. Require telemetry row count, per-device
max sequence, and active telemetry writers to remain unchanged/zero. Then call
`/api/health` and require database, MQTT, active XGBoost, and shadow TCN ready;
also record memory and restart count.

After every gate passes, enable the approved steady-state policy with `docker
update --restart unless-stopped infra-api-c1`. On failure use the unified
graceful-stop procedure.

Do not start `infra-api-1`; database remains migrated and writers remain
stopped.

## 5. Web deployment, read-only check, and rollback

Only after the API gate passes, record the stopped/running old Web identity and
its approved image ID. Stop old Web; retain its exited container for rollback.
Start C1 Web on the captured network and port, with the C1 image ID:

```bash
# Execute the Unified fail-closed graceful stop procedure above for infra-web-1.
docker run -d --name infra-web-c1 --label com.docker.compose.project=infra \
  --label com.docker.compose.service=web --restart=no --memory 128m \
  --network "$WEB_NETWORK" -p "127.0.0.1:${WEB_PORT}:80" "$WEB_SOURCE_IMAGE_ID"
```

Require one running `infra/web` label selection, then browse only historical
data: dashboard, wells, history, and alarms. Require proxy success and no
blocking browser error. No telemetry test is allowed.

After Web gates pass run `docker update --restart unless-stopped infra-web-c1`.
Web-only rollback uses the unified graceful-stop procedure for C1, then starts
only the retained approved old Web container:

```bash
# Execute the Unified fail-closed graceful stop procedure above for infra-web-c1.
docker start infra-web-1
docker inspect --format '{{.State.Status}}|{{.Image}}' infra-web-1
```

This rollback does not alter API, database, or Edge.

## 6. Edge named volume and atomic state initialization

The Compose logical volume is `edge-state`; resolve its actual runtime name on
the Pi into `$EDGE_STATE_VOLUME` and record `docker volume inspect`. It must be
a named local volume, not temporary container storage. Before state work,
verify one or zero stopped Edge containers and **zero running writers** for
`edge-pi-01`; verify broker/API/database no-write evidence again.

`flock` only protects processes accessing the same lock file. Production must
therefore enforce `EDGE_DEVICE_ID -> exactly one canonical persistent /state
runtime volume`. For `edge-pi-01`, record that volume identity, require every
future C1 instance to mount it, and prohibit a second normal state volume,
container-local state, deletion, rollback, or replacement to bypass ownership.
Lost or ambiguous volume identity is No-Go: stop writers, read fresh DB
high-water, and use controlled recovery rather than starting Edge.

Read fresh `M` from production at execution time, never from this document:

```sql
SELECT max(t.sequence) AS max_sequence
FROM public.telemetry AS t
WHERE t.device_id = 'edge-pi-01';
```

Use the C1 Edge image as a helper with the named volume. It first imports the
actual production `SingleWriterLock` for the same device and obtains flock.
Lock contention is No-Go with no state update. This exact initializer
rejects malformed state, writes a temporary file, fsyncs it, atomically renames,
fsyncs the parent directory, and re-reads the result. It does not send MQTT.

```bash
docker run --rm -i --mount "type=volume,src=${EDGE_STATE_VOLUME},dst=/state" \
  --entrypoint python "$EDGE_SOURCE_IMAGE_ID" - "$M" "$EDGE_DEVICE_ID" <<'PY'
import json, os, sys
from pathlib import Path
from edge_agent.single_writer import SingleWriterLock
m = int(sys.argv[1]); device_id = sys.argv[2]; path = Path('/state/sequence.json'); u = 0
lock = SingleWriterLock(path.parent, device_id)
lock.acquire()
if path.exists():
    old = json.loads(path.read_text())
    if old.get('schema') != 1 or not isinstance(old.get('reserved_until'), int):
        raise SystemExit('No-Go: malformed existing sequence state')
    u = old['reserved_until']
value = max(m, u); temporary = path.with_suffix('.tmp')
with temporary.open('w') as output:
    json.dump({'schema': 1, 'reserved_until': value}, output)
    output.flush(); os.fsync(output.fileno())
os.replace(temporary, path)
directory = os.open('/state', os.O_RDONLY)
try: os.fsync(directory)
finally: os.close(directory)
if json.loads(path.read_text()) != {'schema': 1, 'reserved_until': value}:
    raise SystemExit('No-Go: state reread mismatch')
print(value)
PY
```

Record `M`, existing `U` (zero if absent), and the written value. Require it
to be at least `M` and below `9007199254740991`.

## 7. Edge deployment and no-write gate

Start only after API/Web gates and state initialization. Use the Pi-captured
network, environment file, MQTT parameters, and `/data` bind source; do not
guess them. The shell wrapper fixes `umask 077`, which isolated verification
confirmed preserves `/state/sequence.json` as mode `0600` after allocator
lease writes.

```bash
docker run -d --name edge-agent-c1 \
  --label com.docker.compose.project=edge \
  --label com.docker.compose.service=edge-agent \
  --label oilwell.device_id=edge-pi-01 \
  --restart=no --network "$EDGE_NETWORK" --env-file "$EDGE_ENV_FILE" \
  -e EDGE_SEQUENCE_FILE=/state/sequence.json -e EDGE_REPLAY_AUTOSTART=false \
  --mount "type=volume,src=${EDGE_STATE_VOLUME},dst=/state" \
  --mount "type=bind,src=${EDGE_DATA_SOURCE},dst=/data,readonly" \
  --entrypoint sh "$EDGE_SOURCE_IMAGE_ID" -c 'umask 077; exec python -m edge_agent.main'
```

Before and after start, run the runtime writer-count gate. It must return
exactly one only after C1 starts; two or more is immediate No-Go and requires
stopping `edge-agent-c1` without touching state.

`SingleWriterLock` acquires a per-device non-blocking persistent-volume flock
before `SequenceAllocator`, MQTT, heartbeat, or replay. A duplicate exits
non-zero with `single writer lock already held`, without allocator entry or
sequence-state modification. Docker writer count remains defense-in-depth, not
the primary correctness mechanism.

```bash
docker ps -q --filter label=com.docker.compose.service=edge-agent \
  --filter label=oilwell.device_id=edge-pi-01 | wc -l
```

Require C1 image/mount identity, heartbeat ONLINE, selected instance reported,
replay STOPPED/not replaying, readable state, and unchanged telemetry count.
Read state after allocator startup: `new_reserved_until > M` and below the
safe-integer limit. Do not send START or any telemetry.

After all Edge gates pass run `docker update --restart unless-stopped
edge-agent-c1`. On failure use the unified graceful-stop procedure; retain the
canonical volume and lock file.

Edge failure rollback:

```bash
# Execute the Unified fail-closed graceful stop procedure above for edge-agent-c1.
docker volume inspect "$EDGE_STATE_VOLUME"
```

Never remove the canonical volume, lock file, or state to "unlock"; never lower
`reserved_until`, switch to a second state volume, or start old Edge replay.
Kernel flock releases on process exit; lock-file presence is not ownership.

## 8. Non-production validation record and resolved ownership gate

The following operations were exercised with isolated Docker names/network and
no production mount, credential, host, or telemetry:

- API archive save/load identity retained the approved ID/architecture.
- API create/start/stop worked with temporary PostgreSQL/MQTT and read-only
  local model mounts; `/api/health` reported both slots ready. A second API
  startup left constraint definitions/OIDs unchanged; one-running-API label
  gate passed.
- Web replacement and rollback to a retained old container passed.
- Named-volume atomic initialization, file/parent fsync, re-read, and state
  persistence across Edge stop passed. The umask-wrapped Edge command left the
  state file mode `0600`.

**Resolved:** `1d13bc8` adds the actual `SingleWriterLock` implementation:
per-device `LOCK_EX | LOCK_NB` flock on persistent `/state`, held for the
process lifetime before allocator/MQTT/heartbeat/replay. Container A acquired
the lock on a shared named volume; B with the same device exited non-zero with
`single writer lock already held`, did not enter the allocator, and left
`sequence.json` SHA-256 unchanged. After abnormal A termination, C acquired
the same flock and advanced `reserved_until` from `1789289816242248` to
`1789289862298957`. These are isolation evidence only, never production
initialization values. Separate device IDs held separate locks concurrently.

## 9. Final Go/No-Go checklist

- [ ] New maintenance ID; fresh runtime/catalog/resource evidence.
- [ ] Archive SHA-256, destination image ID, and architecture chain verified.
- [ ] Pi target identity was freshly verified only through the protected target record.
- [ ] Old Edge replay was proven stopped, then old Edge exited through the graceful retirement gate.
- [ ] Runtime writer count is zero and broker/database no-write observations are stable before C1 API.
- [ ] Old API stopped; writers and replay stopped; C1 API only one running.
- [ ] Exact model hashes/read-only mounts verified.
- [ ] API startup catalog/OID/no-write/health/resource gates pass.
- [ ] Web historical-data gate passes or Web-only rollback completed.
- [ ] Edge image source is `1d13bc8` and identity matches the approved candidate.
- [ ] Canonical persistent `/state` volume identity is fixed for `edge-pi-01`.
- [ ] Single-writer flock is applicable and validated; writer count before start is 0.
- [ ] State initialization uses fresh `M`, valid `U`, atomic/fsync helper, and reread.
- [ ] Edge startup acquires writer lock; writer count after start is 1.
- [ ] `reserved_until` advances monotonically; replay remains stopped; telemetry remains unchanged.

All Edge checklist items remain mandatory. A 240-point replay always requires
another independent authorization.
