# Phase A.3 C1 production deployment execution — `phase-a3-20260913T0915Z`

## Result

**ABORT — No-Go before any deployment mutation.**

The maintenance window started at `2026-09-13T10:16:39Z` and was stopped at
`2026-09-13T10:16:58Z`. No image archive was transferred or loaded; no C1
container was created, started, stopped, or restarted; no production state
volume was created or initialized; and replay was not started.

## Approved baselines not acted on

| Component | Approved source / candidate |
| --- | --- |
| API | `6eb90bbc3d2cb850194d223f66805e0e3c19feec` |
| Web | audited C1 / `6eb90bb` artifact |
| Edge | `1d13bc8`; candidate `sha256:f0284dee673fc229145e9f8b5b68000ed7e7993a6ce361493323be3d136375bc` (`linux/arm64`) |

No artifact identity chain was accepted in this window, so none of these
baselines was deployed.

## Fresh preflight and Abort evidence

| Gate | Result | Evidence / reason |
| --- | --- | --- |
| Maintenance ID | Recorded | `phase-a3-20260913T0915Z`; this is a new window and does not reuse a prior window's Go evidence. |
| ECS runtime capture | **No-Go** | The first fresh, read-only container capture began at `2026-09-13T10:16:39Z` but failed before emitting container data because the Docker formatting template requested unsupported field `.ImageID`. This is an operational preflight-command failure; it was not retried. |
| Registered Pi target and capture | **No-Go** | No uniquely identified, approved production Pi endpoint was available from the controlled deployment material or local SSH host configuration. Therefore the required fresh old-Edge identity, canonical volume, mount, runtime UID/GID, and resource capture could not be obtained without guessing a target. |
| Model hashes, protected env capture, catalog baseline, resources | Not accepted | These gates were not completed after the preflight failure and may not be inferred from an earlier window. |
| Artifact transfer/load | Not attempted | No archive SHA-256 receipt, destination image ID, or target architecture chain was created. |
| API deployment/catalog gate | Not attempted | No C1 API container was started. |
| Web deployment/read-only gate | Not attempted | No Web container change was made. |
| Canonical `/state`, locked initialization, Edge gate | Not attempted | No Pi action, volume action, sequence initialization, lock acquisition, heartbeat, or telemetry operation occurred. |

## Production state at Abort

The requested C1 deployment was not begun. The intended protected state remains:

- Database: migrated / ready for C1 deployment.
- Old API: stopped; it was not started.
- Telemetry writers and Pi replay: not operated by this window.
- C1 API, Web, and Edge: not deployed by this window.
- Edge `/state`: not created or initialized by this window.
- Replay: not started; no production telemetry was sent.

No DDL, DML, model change, threshold change, state rollback, or recovery action
was performed. No COMMIT was attempted.

## Required next authorization

A later deployment attempt requires a **new** maintenance ID and must restart
from Artifact verification and fresh preflight. Before it can reach Edge work,
the operator must provide or register one verifiable production Pi target so
the Runbook's required fresh runtime and canonical-volume capture can be made.
The Docker runtime capture command must also be corrected and non-production
validated before reuse; this window's failed command and all prior Go evidence
remain ineligible for reuse.
