# System acceptance scenarios

1. Start the cloud compose stack with secrets and TLS material supplied outside Git.
2. Start the Pi edge-agent with a mounted selected 3W Parquet instance.
3. Verify `ONLINE`/`REPLAYING` heartbeats, telemetry persistence, WebSocket updates and the 10×/20× controls.
4. Replay a labelled abnormal instance and verify the resulting teaching alarm can be acknowledged.
5. Disconnect MQTT temporarily and verify the device becomes stale/offline in operational monitoring before reconnecting.
