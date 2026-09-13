# Phase A.2 production database migration — execution record

- Maintenance ID: `phase-a2-20260913T0801Z`
- Runbook revision: `df93cc5`
- Started: `2026-09-13T08:01:17Z`
- Completed: `2026-09-13T08:13:34Z`
- Result: **GO — Database ready for C1 deployment**

This is an execution summary only. Protected backup locations, credentials,
container IDs, raw catalog extracts, and raw service evidence are intentionally
excluded from Git.

## Stage results

| Stage | Result | Public evidence summary |
| --- | --- | --- |
| Preflight A | GO | PostgreSQL 16.15; `telemetry.sequence=int4`; `alarms.resolved_at` absent; target UNIQUE constraints valid and ready; resource checks acceptable. |
| Stop Writes / Drain | GO | Fresh Pi STOP request was accepted. Three pre-stop Drain snapshots, a 12-second clean MQTT telemetry audit, and two post-stop Drain snapshots showed no telemetry movement, no retained telemetry, and zero active telemetry write transactions. |
| API graceful stop | GO | The single label-selected `infra/api` runtime identity matched this window's fixed container/image/PID/StopSignal record. One `SIGTERM` was sent; the API exited in 3.232 seconds. No force-kill, second signal, Compose command, restart, recreate, or start was used. PostgreSQL, Mosquitto, and Web remained running with unchanged runtime identities. |
| Fresh backup | GO | New custom-format and schema-only backups were created in a protected non-Git location, mode `0600`, non-empty, and custom backup listability was verified. |
| Final schema/data assertion | GO | Pre-DDL row counts were telemetry 3817, alarms 2, inference_results 7634. Device `edge-pi-01` had count/min/max `3817/1/1789216640`; sequence signature was `d664cf6ac8f10af3c29527717524fbb6`. |
| Approved DDL | GO | The approved transaction completed with explicit `COMMIT`; no third schema change was executed. |
| Post-migration database validation | GO | Row counts, per-device values, and sequence signature were unchanged; `sequence` is `int8`; `resolved_at` is nullable `timestamptz`; both existing alarm rows have `resolved_at IS NULL`. |

## Backup integrity record

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Custom-format full backup | 272730 | `c07541cf302b018d9e0acb968d55c761c557add986bc1a567fe599cac6eca5aa` |
| Schema-only backup | 14417 | `38768073e354d55f8b6d5e50b10efbc0bdc105509e917e04c8195e09b18cc5be` |

The custom backup's listing artifact was also non-empty and readable; its
SHA-256 was `b32a36017cab4bdb8bf15dd43fd868bf4ee65f941c8aff68ec9e724156da9e3b`.

## Catalog validation

- `uq_inference_telemetry_model_mode`: definition, constraint OID, and backing
  index OID were all unchanged.
- `uq_telemetry_device_sequence`: remains a validated UNIQUE constraint on
  `public.telemetry(device_id, sequence)` with a valid and ready backing index.
- All other public constraints, foreign keys, and indexes retained their
  definitions and OIDs.
- Physical `relfilenode` changes were recorded for telemetry-table indexes
  during the approved table rewrite. They were not OID or definition changes;
  the Runbook records them for audit and does not define them as an automatic
  failure gate for unrelated objects.

## Final production state

- Database: migrated; ready for C1 deployment only.
- Old API: exited/stopped; not restarted.
- Pi replay and telemetry publishers: STOP requested and telemetry inactivity
  verified; not resumed.
- C1 API/Web/Edge: not deployed.
- Edge `/state`: not initialized.

No C1 deployment, API HTTP call after stop, service restart, Compose command,
or production telemetry send was performed after the migration.
