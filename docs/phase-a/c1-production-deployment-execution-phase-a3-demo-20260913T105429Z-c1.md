# C1 controlled deployment execution — `phase-a3-demo-20260913T105429Z`

## Result

**PASS — C1 deployed; replay remains STOPPED.**

Deployment completed at `2026-09-13T12:20:00Z`. The later 240-point replay is
an independent operation and was not started by this deployment record.

## Deployment summary

| Component | Result |
| --- | --- |
| Database | Already migrated; telemetry sequence remains `BIGINT`; alarms `resolved_at` remains nullable `TIMESTAMPTZ`. |
| Old API | Remains exited; it was not restarted. |
| C1 API | Running with the approved amd64 artifact, protected old-runtime environment, read-only model mounts, and `unless-stopped`. Health reports database/MQTT/active XGBoost/shadow TCN ready. |
| C1 Web | Running with the approved amd64 artifact and `unless-stopped`; dashboard and historical API paths returned HTTP 200. |
| Old Edge | Retired only after fresh identity/no-write verification and the separately authorized one-time SIGKILL following its failed graceful stop. Its container and historical data remain retained. |
| C1 Edge | Running with replay disabled, `unless-stopped`, one canonical persistent `edge-state` volume, and a verified `SingleWriterLock`. |

## Integrity and no-write gates

- Model hashes matched the approved active XGBoost and shadow TCN artifacts.
- C1 API startup preserved `uq_inference_telemetry_model_mode` definition and
  constraint/backing-index identities (`24613` / `24612`).
- Edge state was initialized from fresh `M=1789216640`; the running allocator
  advanced `reserved_until` to `1789301791046471`, below the JavaScript safe
  integer limit and above `M`.
- `sequence.json` is persistent and mode `0600`; runtime writer count is one.
- C1 Edge logged successful MQTT connection and publishes ONLINE status through
  the existing heartbeat path; replay autostart is explicitly false.
- Telemetry remained unchanged through deployment: `edge-pi-01` count `3817`,
  maximum sequence `1789216640`, and active telemetry writes `0`.

## Minimal runtime correction

The manually created C1 Edge initially timed out connecting to MQTT because
the old Edge's Docker `extra_hosts` hostname override was omitted. The old,
verified override was restored after a short non-publishing socket probe passed.
The failed C1 Edge container was removed; the canonical volume/state was kept
unchanged. No model, schema, threshold, data, or sequence algorithm was
changed.

## Final state

`C1 deployed, replay not authorized`.

The next required operation is a separately authorized, one-time 240-point
controlled replay using the existing API command path. It must record source
instance, well, timestamps, seven variables, counts, sequences, inference,
WebSocket, and Vue results.
