# C1 controlled deployment execution — `phase-a3-demo-20260913T105429Z`

## Result

**ABORT — old Edge did not exit after the single approved graceful-stop signal.**

Window start: `2026-09-13T10:54:29Z`.

The fixed old Edge container was verified as the uniquely registered
`edge-pi-01` instance. It had no configured StopSignal, so it received one
`SIGTERM`. It remained `running=true` throughout the full 20-second observation
window. No second signal, `SIGKILL`, `docker stop`, restart, removal, Compose
operation, state deletion, or replay command was used.

## Completed evidence

| Gate | Result |
| --- | --- |
| Fresh Pi identity | PASS: protected target record, hostname, machine-id hash, `aarch64`, Docker, exactly one old Edge, and `edge-pi-01` matched. |
| Database/no-write preflight | PASS: migrated schema; telemetry count/max for `edge-pi-01` remained `3817` / `1789216640`; active telemetry writes were zero. |
| Old Edge replay configuration | PASS: `EDGE_REPLAY_AUTOSTART=false`; no configured replay file. |
| API/Web artifact transfer | PASS: destination archive SHA-256 values matched the approved local archives; images loaded on ECS. |
| Edge artifact transfer | PASS: destination archive SHA-256 matched; archive config digest, arm64 platform, command, RootFS layers, and actual `SingleWriterLock` module were verified. Pi Docker reported a locally rewritten imported image ID, so the Edge candidate was not deployed. |
| Old Edge graceful retirement | **FAIL / Abort**: one `SIGTERM`; still running after 20 seconds. |

## Final production state

- Database remains migrated; telemetry count/max is unchanged at `3817` /
  `1789216640`.
- Old API remains exited.
- Old Web remains running.
- Old Edge remains running; no C1 Edge container was created.
- No C1 API or C1 Web container was created.
- No production `/state` volume or sequence state was created or initialized.
- No replay was started and no production telemetry was intentionally sent.

## Required next decision

The C1 deployment cannot continue while the existing Edge process remains
running. Continuing would require an explicit, separately authorized way to
retire or otherwise safely control that process; this window must not reuse its
maintenance evidence.
