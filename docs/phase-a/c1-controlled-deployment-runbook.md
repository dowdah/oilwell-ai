# Phase A.3.1 — C1 Controlled Deployment Runbook

## 0. Authority, fixed state, and stop boundary

This Runbook is prepared and non-production validated, but **is not deployment
authority**. A future execution needs a new maintenance ID and explicit
approval. Until then, production remains: database migrated; old API stopped;
writers/Pi replay stopped; C1 absent; Edge `/state` uninitialized.

Stop after this fixed sequence; do not enter 240-point replay:

```text
Artifact verification → API deployment → API catalog/no-write gate
→ Web deployment → Web read-only gate → Edge state volume
→ fresh DB MAX(sequence) → state initialization
→ Edge deployment with replay stopped → Edge heartbeat/state/no-write gate
```

Never use Compose in this procedure: current production Compose interpolation
is not an approved control path. Never start old API or old Edge as rollback.
All evidence paths below are protected, non-Git paths under
`$MAINT_EVIDENCE_DIR`; no passwords, private keys, tokens, or full connection
strings may be copied into the change record.

## 1. Fixed source and image identity chain

Runtime source is exactly `6eb90bbc3d2cb850194d223f66805e0e3c19feec`,
the direct C1 child containing the idempotent inference-constraint fix. Do not
build from the ordinary workspace, which contains C2 research changes.

| Component | Platform | source image ID |
| --- | --- | --- |
| API | `linux/amd64` | `sha256:b5ea8ecbd6df7276a94cb8abf357b0ade629d2560792a3703fdff0e6d77d0ae6` |
| Web | `linux/amd64` | `sha256:21276fb2ef65ad108ad61a3c4ff937e015b07f303a01663803050254ea9a0753` |
| Edge | `linux/arm64` | `sha256:676f40baf3d7d775f52702af96585516afe4a390a58b5ec7bd873fe0cf85badf` |

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

Before Edge work, run the same sanitized capture on the registered Pi host for
the old Edge container. Its host identity, logical/runtime volume name,
environment names, `/data` mount, UID/GID, MQTT endpoint parameters, and
device label must be obtained afresh. Without a uniquely identified Pi target
and capture, Edge is No-Go.

```bash
# Approved read-only capture template; do not print environment values.
docker inspect "$CONTAINER_ID" > "$MAINT_EVIDENCE_DIR/runtime-raw.json"
docker inspect --format '{{.Id}}|{{.Image}}|{{.State.Status}}|{{.Path}}|{{json .Args}}|{{json .Config.Entrypoint}}|{{json .HostConfig.PortBindings}}|{{json .NetworkSettings.Networks}}|{{json .Mounts}}|{{json .HostConfig.RestartPolicy}}|{{.Config.User}}|{{.Config.WorkingDir}}|{{.HostConfig.Memory}}|{{.HostConfig.NanoCpus}}' "$CONTAINER_ID" > "$MAINT_EVIDENCE_DIR/runtime-sanitized.txt"
docker inspect --format '{{range .Config.Env}}{{println (index (split . "=") 0)}}{{end}}' "$CONTAINER_ID" | sort -u > "$MAINT_EVIDENCE_DIR/environment-names.txt"
```

Use the observed mounts/networks/ports/environment names; never reconstruct
them from memory. Also record host available memory, each container's memory
and CPU, total container use, and restart counts. OOM, swap/thrashing, repeated
restart, or resource exhaustion is No-Go.

## 3. API deployment and catalog gate

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
  --restart unless-stopped --memory 512m --network "$API_NETWORK" \
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

Any failed catalog, health, model, resource, or no-write check is Abort:

```bash
docker stop --time 20 infra-api-c1
docker inspect --format '{{.State.Status}}|{{.State.FinishedAt}}' infra-api-c1
```

Do not start `infra-api-1`; database remains migrated and writers remain
stopped.

## 4. Web deployment, read-only check, and rollback

Only after the API gate passes, record the stopped/running old Web identity and
its approved image ID. Stop old Web; retain its exited container for rollback.
Start C1 Web on the captured network and port, with the C1 image ID:

```bash
docker stop --time 20 infra-web-1
docker run -d --name infra-web-c1 --label com.docker.compose.project=infra \
  --label com.docker.compose.service=web --restart unless-stopped --memory 128m \
  --network "$WEB_NETWORK" -p "127.0.0.1:${WEB_PORT}:80" "$WEB_SOURCE_IMAGE_ID"
```

Require one running `infra/web` label selection, then browse only historical
data: dashboard, wells, history, and alarms. Require proxy success and no
blocking browser error. No telemetry test is allowed.

Web-only rollback is concrete:

```bash
docker stop --time 20 infra-web-c1
docker inspect --format '{{.State.Status}}' infra-web-c1
docker start infra-web-1
docker inspect --format '{{.State.Status}}|{{.Image}}' infra-web-1
```

This rollback does not alter API, database, or Edge.

## 5. Edge named volume and atomic state initialization

The Compose logical volume is `edge-state`; resolve its actual runtime name on
the Pi into `$EDGE_STATE_VOLUME` and record `docker volume inspect`. It must be
a named local volume, not temporary container storage. Before state work,
verify one or zero stopped Edge containers and **zero running writers** for
`edge-pi-01`; verify broker/API/database no-write evidence again.

Read fresh `M` from production at execution time, never from this document:

```sql
SELECT max(t.sequence) AS max_sequence
FROM public.telemetry AS t
WHERE t.device_id = 'edge-pi-01';
```

Use the C1 Edge image as a helper with the named volume. This exact initializer
rejects malformed state, writes a temporary file, fsyncs it, atomically renames,
fsyncs the parent directory, and re-reads the result. It does not send MQTT.

```bash
docker run --rm -i --mount "type=volume,src=${EDGE_STATE_VOLUME},dst=/state" \
  --entrypoint python "$EDGE_SOURCE_IMAGE_ID" - "$M" <<'PY'
import json, os, sys
from pathlib import Path
m = int(sys.argv[1]); path = Path('/state/sequence.json'); u = 0
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

## 6. Edge deployment and no-write gate

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
  --restart unless-stopped --network "$EDGE_NETWORK" --env-file "$EDGE_ENV_FILE" \
  -e EDGE_SEQUENCE_FILE=/state/sequence.json -e EDGE_REPLAY_AUTOSTART=false \
  --mount "type=volume,src=${EDGE_STATE_VOLUME},dst=/state" \
  --mount "type=bind,src=${EDGE_DATA_SOURCE},dst=/data,readonly" \
  --entrypoint sh "$EDGE_SOURCE_IMAGE_ID" -c 'umask 077; exec python -m edge_agent.main'
```

Before and after start, run the runtime writer-count gate. It must return
exactly one only after C1 starts; two or more is immediate No-Go and requires
stopping `edge-agent-c1` without touching state.

```bash
docker ps -q --filter label=com.docker.compose.service=edge-agent \
  --filter label=oilwell.device_id=edge-pi-01 | wc -l
```

Require C1 image/mount identity, heartbeat ONLINE, selected instance reported,
replay STOPPED/not replaying, readable state, and unchanged telemetry count.
Read state after allocator startup: `new_reserved_until > M` and below the
safe-integer limit. Do not send START or any telemetry.

Edge failure rollback:

```bash
docker stop --time 20 edge-agent-c1
docker inspect --format '{{.State.Status}}|{{.State.FinishedAt}}' edge-agent-c1
docker volume inspect "$EDGE_STATE_VOLUME"
```

Never remove the volume, lower `reserved_until`, or start old Edge replay.

## 7. Non-production validation record and blocking finding

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

**Blocking finding:** C1 `SequenceAllocator` has no inter-process ownership
lock. In isolation, a second Edge with the same device label could start and
advance the shared state; the writer-count command detects this only after it
exists. Therefore the duplicate-writer requirement is **not fail-closed** and
this Runbook is not eligible for production Edge deployment until a separately
approved code/runtime ownership control is implemented and revalidated. API and
Web planning remains usable, but the full sequence through Edge must stop at
this No-Go.

## 8. Final Go/No-Go checklist

- [ ] New maintenance ID; fresh runtime/catalog/resource evidence.
- [ ] Archive SHA-256, destination image ID, and architecture chain verified.
- [ ] Old API stopped; writers and replay stopped; C1 API only one running.
- [ ] Exact model hashes/read-only mounts verified.
- [ ] API startup catalog/OID/no-write/health/resource gates pass.
- [ ] Web historical-data gate passes or Web-only rollback completed.
- [ ] Pi runtime capture uniquely identifies Edge configuration and volume.
- [ ] State initialization uses fresh `M`, valid `U`, atomic/fsync helper, and reread.
- [ ] **Blocked:** duplicate-writer fail-closed control implemented and separately validated before any C1 Edge start.

Without the final item, do not initialize production `/state`, start C1 Edge,
or enter replay. A 240-point replay always requires another independent
authorization.
