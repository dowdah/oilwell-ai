# Phase A final controlled replay — `phase-a-final-20260913T123844Z`

## Result

**PASS — `Phase A engineering closed-loop: PASS`.**

The replay was stopped cleanly. No production schema, model, threshold, or
sequence-state change was made during this maintenance window. The full
Edge → MQTT → API → PostgreSQL → inference → WebSocket → Vue path was
observed through the production HTTPS entry point.

## Scope and source

| Item | Evidence |
| --- | --- |
| Maintenance window | 2026-09-13T12:38:11Z–12:48:11Z (UTC) |
| Source instance | `WELL-00014_20160304155906.parquet` |
| Source category | Approved 3W parquet instance |
| Derived / configured well | `WELL-00014` / `WELL-00014` — matched |
| Source range used | 2016-03-04T15:59:06Z through 2016-03-04T16:03:05Z |
| Source contract | 240 rows; timestamp plus P-PDG, P-TPT, T-TPT, P-MON-CKP, T-JUS-CKP, P-JUS-CKGL, and QGL all present and non-null |

The source file has 70,944 rows, so the selected first 240 rows are a
continuous subset. A read-only canonical SHA-256 over every replayed row's
UTC timestamp, `well_id`, and seven IEEE-754 measurement values matched
exactly between source and PostgreSQL:

```
7d4d56ada578216e9aab913a717e506311c6b84ce1779087d976f4721d71850d
```

No raw telemetry payload is retained in this record.

## Baseline and controlled commands

Before any command, PostgreSQL contained 3,817 telemetry rows, all for
`edge-pi-01`; the maximum sequence was 1,789,216,640. There were 7,634
inference rows, two alarms, and zero active telemetry-writing sessions. C1
API health was `ok` with MQTT connected and inference ready. C1 Edge was the
only writer, held its `SingleWriterLock`, reported `ONLINE`, and reported an
empty selected replay instance.

The existing approved API command path accepted and Edge applied, in order:

1. `LOAD_INSTANCE` for `WELL-00014_20160304155906.parquet` while Edge remained `ONLINE`.
2. `SET_SPEED` to `1`.
3. `START`.
4. `STOP` when the database reached the exact target count of 4,057.

The STOP command was applied at 2026-09-13T12:42:43.865234Z. Edge then
reported `ONLINE`, not replaying, and remained running.

## Data and sequence result

| Check | Result |
| --- | --- |
| Telemetry before / after | 3,817 / 4,057 |
| New valid samples | **240** |
| New sequence range | 1,789,301,791,036,472–1,789,301,791,036,711 |
| Distinct sequences | 240 |
| Sequence span | 240; strictly contiguous and all above the pre-replay database maximum |
| Wrong-well rows | 0 |
| Rows missing any of seven variables | 0 |
| State / allocator evidence | Edge ended at the replay maximum; persistent reserved high-water remained above the replay range |
| Post-STOP stability | telemetry remained 4,057; maximum remained 1,789,301,791,036,711; active telemetry-writing sessions were 0 |

## Inference and alarm result

The 240 continuous 1 Hz samples produced the actual 180-point/10-second
stride result:

| Mode | Warm-up records | Predicted full windows | Latency for predicted windows |
| --- | ---: | ---: | --- |
| Active XGBoost | 179 | 7 | 3.913–14.260 ms; mean 6.554 ms |
| Shadow TCN | 179 | 7 | 3.868–83.297 ms; mean 17.484 ms |

There were therefore 372 persisted inference records associated with the new
telemetry: 179 warm-up plus 7 predicted outcomes for each of the two model
modes. The seven predicted windows span the replay from the first source time
to 2016-03-04T16:03:05Z. This is the expected operational representation of
the model contract: warm-up records are persisted for the first 179 samples,
then seven full windows are produced at the 10-second stride.

Alarm count remained two. **Engineering inference path passed; real-model
alarm trigger not observed.** No threshold, model, prediction, or source label
was altered to force an alarm.

## WebSocket and Vue result

The temporary read-only WebSocket observer connected to the deployed API and
received both event types for `WELL-00014`:

- telemetry event: sequence 1,789,301,791,036,472 at
  2016-03-04T15:59:06Z;
- inference event: the associated `WELL-00014` inference was delivered on the
  same connection (initial warm-up event for telemetry id 7,295).

The API WebSocket event path therefore passed. The C1 Web container is
intentionally a static SPA container; the established deployment architecture
places `/api` and `/ws` forwarding in the ECS host HTTPS Nginx proxy. An
initial direct check of the Web container's loopback port bypassed that proxy
and was discarded as an invalid browser acceptance path.

The corrected production HTTPS check returned both configured wells from
`/api/wells`. A browser then selected `WELL-00014` and showed `实时连接正常`,
the active predicted inference, and rendered the seven-variable ECharts
series: P_PDG, P_TPT, T_TPT, P_MON_CKP, T_JUS_CKP, P_JUS_CKGL, and QGL. No
blocking UI error was visible. The external proxy and the C1 Web container
were not changed during this verification.

## Final production state

- Database remains migrated and healthy.
- C1 API remains healthy, MQTT-connected, and inference-ready.
- C1 Web remains running and its production HTTPS API/WebSocket/Vue gate has
  passed.
- C1 Edge remains running, is the sole writer, holds the single-writer lock,
  reports `ONLINE`, and has replay stopped.
- Telemetry is stable at 4,057 rows; no writers are active.
- Old API and old Edge remain stopped.

## Phase A closure

`Phase A engineering closed-loop: PASS`.

The active XGBoost result is recorded as observed; it is not a claim that the
model is reliable across wells or event types. The next project phase is the
separately scoped binary anomaly-detection product migration; it is not part
of this replay maintenance window.
