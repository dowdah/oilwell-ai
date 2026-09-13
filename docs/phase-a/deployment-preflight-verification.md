# Phase A.3.2 — Production target registration and preflight hardening

## Result

| Gate | Result |
| --- | --- |
| ECS Docker runtime capture | PASS in isolated Docker validation |
| Production Pi target registration | BLOCKED — registration required |
| Production Pi identity verification | Not attempted; no registered target |
| Deployment Runbook update | Deferred until both preceding gates pass |

No production API, Web, Edge, state volume, sequence state, replay, telemetry,
or database operation was performed in this phase.

## Original capture failure and correction

The Phase A.3 Abort used a container-listing template containing `.ImageID`.
That field is not available on the Docker container formatting context, so the
read-only command failed before it could produce a runtime capture.

Container identity must instead be recorded as follows:

- `.Id`: immutable container ID.
- `.Image`: immutable image ID.
- `.Config.Image`: configured image reference; it is not image identity.

`StopSignal` is optional in the inspected configuration. The isolated test also
showed that direct `.Config.StopSignal` access fails when the key is absent.
Use the optional form `{{with index .Config "StopSignal"}}{{.}}{{end}}`; an
empty result is then mapped to `SIGTERM` by the Runbook's graceful-stop logic.

The corrected read-only capture command is:

```bash
docker inspect --format '{{.Id}}|{{.Name}}|{{.Image}}|{{.Config.Image}}|{{.State.Status}}|{{.State.Pid}}|{{.State.StartedAt}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{json .HostConfig.PortBindings}}|{{json .NetworkSettings.Networks}}|{{json .Mounts}}|{{json .HostConfig.RestartPolicy}}|{{.HostConfig.Memory}}|{{.HostConfig.NanoCpus}}|{{.Config.User}}|{{.Config.WorkingDir}}|{{with index .Config "StopSignal"}}{{.}}{{end}}' "$CONTAINER_ID"
docker inspect --format '{{range .Config.Env}}{{println (index (split . "=") 0)}}{{end}}' "$CONTAINER_ID" | sort -u
```

The environment command emits names only. Actual values remain confined to the
protected `0600` non-Git environment file created from the approved old
container during an authorized deployment window.

## Isolated Docker verification

The corrected command was exercised against two disposable `alpine:3.20`
containers sharing an isolated named volume and network:

| Case | Result |
| --- | --- |
| Running container with `SIGTERM`, Compose-style labels, mount, network, and environment | PASS; exit 0 and all required fields emitted. |
| Exited container without configured `StopSignal`, Compose-style labels, mount, network, and environment | PASS; exit 0, empty StopSignal field, and no missing-key error. |
| Immutable image identity | PASS; container `.Image` exactly matched `docker image inspect --format '{{.Id}}'` for that image. |
| Side effects | PASS; capture commands only inspected state. Test containers, network, and volume were removed after validation. |

No Compose configuration was parsed. The test deliberately did not use a
production container, mount, environment value, endpoint, or credential.

## C1 deployment Runbook Docker-template audit

All Docker Go templates in
`docs/phase-a/c1-controlled-deployment-runbook.md` were reviewed.

| Template use | Audit result |
| --- | --- |
| `.ImageID` | Absent. |
| `.Id`, `.Image`, `.Config.Image`, `.State.*`, `.HostConfig.*`, `.Config.User`, `.Config.WorkingDir`, `json` network/mount fields | Validated by the isolated running/exited capture. |
| `.Config.StopSignal` in unified graceful-stop procedure | Requires the optional `index` form above before production reuse. |
| `range .Config.Env` with `split` | Validated; records names only. |
| `docker image inspect` `.Id`, `.Os`, `.Architecture` | Uses image-inspect context, not container context; no unsupported container field is involved. |

One separate optional-StopSignal occurrence remains in the Phase A.2 database
migration Runbook. It was identified for a separately authorized documentation
correction and was not altered in this phase.

## Production Pi target registration status

The required Git-ignored target-record location is available at
`docs/.local/targets/production-edge.json`. Existing protected local material
did not contain a uniquely correlated Pi endpoint, expected machine-id hash,
hostname, architecture, Docker/old-Edge identity, and `edge-pi-01` device
identity. A generic SSH hint without those correlations is not a valid target
record and was not used.

Before any Pi operation, an operator must create the protected record with at
least:

- logical name `production-edge-pi-01`;
- approved endpoint and permitted SSH user;
- expected machine-id hash, hostname, and `aarch64`/`arm64` architecture;
- expected Docker availability and old-Edge identity;
- `edge-pi-01` device ID;
- registration timestamp and operator/source note; and
- optionally, an approved host-key fingerprint.

The record must not contain a private key, password, token, or other secret and
must not be committed. A deployment window must then connect only to that fixed
endpoint and fail closed on any machine-id, hostname, architecture, Docker,
container-count, or device-ID mismatch. It must not try a fallback host.

## Conclusion

`C1 production preflight tooling: NOT READY`.

ECS capture has a validated correction, but the required production Pi target
is not uniquely registered or identity-verified. Do not update the deployment
Runbook or resume production deployment until that registration and its
read-only identity verification both pass. A subsequent deployment attempt
requires a new maintenance ID and new production evidence.
