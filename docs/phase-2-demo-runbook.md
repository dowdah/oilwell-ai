# Phase 2 demo runbook

## Preconditions

- A validated `ml/artifacts/current/model_metadata.json` and XGBoost artifact exist on the deployment host.
- The selected Pi-mounted directory contains at least one eligible Normal and one eligible abnormal 3W Parquet instance; no full dataset is copied to Pi or ECS.
- MQTT is reachable only over the existing WireGuard/private route, with TLS and per-device ACL credentials.

## Demonstration

1. On Mac, run the inspector, selection, and baseline-training commands in [`ml/README.md`](../ml/README.md). Save the generated manifest, selection table, split, metrics and confusion matrix evidence.
2. Mount the selected Parquet files into the Pi edge-agent `EDGE_DATA_HOST_DIR`; configure only the selected filename, then start the agent and verify its heartbeat in the Edge page.
3. Start replay at 10x and then 20x. Verify `START → telemetry → PostgreSQL → WebSocket → Vue chart → inference` and that the monitor progresses from `warming_up` to `predicted`.
4. Verify `PAUSE`, `SET_SPEED`, `LOAD_INSTANCE`, and `STOP`; record the expected device status after each command.
5. Replay an abnormal instance. Confirm an alarm appears only after two model-confirmed abnormal windows, can be acknowledged, and becomes eligible to fire again only after three Normal windows.

## Evidence and troubleshooting

- Save screenshots of the Edge page, monitor page, model prediction and alarm; redact endpoint addresses and credentials.
- `model_unavailable` means the readonly artifact mount or metadata validation failed. Check `/api/health` and never bypass schema validation.
- `warming_up` is expected until the 180-second timestamp window is complete.
- Invalid or missing 7-variable Parquet instances must be excluded by the manifest rather than filled or replayed.
