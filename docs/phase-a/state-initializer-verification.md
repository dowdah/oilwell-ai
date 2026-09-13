# Locked state initializer — isolated verification

- Edge source: `1d13bc8`
- Candidate image: `sha256:f0284dee673fc229145e9f8b5b68000ed7e7993a6ce361493323be3d136375bc` (`linux/arm64`)
- Volumes: isolated local Docker named volumes only; no production resources.
- Result: **Locked state initializer production gate: PASS**

The probe used the actual production `edge_agent.single_writer.SingleWriterLock`
and the Runbook initializer logic. It did not connect MQTT, API, PostgreSQL, or
replay, and emitted no telemetry.

| Case | Result | Evidence |
| --- | --- | --- |
| 1. Holder contention | PASS | A held `writer-test-edge-01.lock`; initializer exited 1 with `single writer lock already held`. `sequence.json` SHA-256 and `reserved_until` were unchanged; no `.tmp` remained. |
| 2. No holder | PASS | Initializer acquired the actual lock, atomically wrote `max(M,U)`, fsynced file and directory, re-read the same JSON, then exited and released flock. |
| 3. Helper release | PASS | A subsequent actual `SingleWriterLock` + `SequenceAllocator` probe immediately acquired the lock and reserved strictly above initializer high-water. No lock file was deleted. |
| 4. Malformed state | PASS | Invalid JSON caused non-zero exit; original SHA-256 was unchanged and no automatic repair occurred. |
| 5. U > M | PASS | State with `U=500` and `M=100` remained `reserved_until=500`. |
| 6. M > U | PASS | State with `U=100` and `M=200` became `reserved_until=200`. |

The initializer test helper was mounted for isolation with `PYTHONPATH=/app` so
it imported the image's production module exactly as the stdin Runbook helper
does from the image working directory. This was a test-harness path detail, not
a production configuration change.

No code or Runbook defect was found. The remaining production prerequisites are
authorization and fresh production preflight evidence; no deployment was
performed by this verification.
