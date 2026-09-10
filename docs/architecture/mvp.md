# MVP architecture decision record

| Layer | Runtime | Responsibility | Explicit boundary |
| --- | --- | --- | --- |
| Mac | Python / MPS | 3W preparation, experiments, SHAP and model exports | Not production serving |
| Pi 4B | Python + Docker | Parquet batch replay, MQTT publish, heartbeat and command handling | No complete data materialization or mandatory inference |
| ECS 2C2G | Compose | Nginx, FastAPI, PostgreSQL, Mosquitto and static Web | No training, local LLM, Kafka or vector database in P0 |

`event_hint` is optional replay metadata. It makes demo alarms deterministic; it is not a model prediction and must not be presented as such. Once an XGBoost/TCN artifact is loaded, the model adapter becomes the source of `predicted_class`, confidence and explanation.

The RAG/LLM stage is intentionally deferred: it must consume model output, trend summaries and retrieved documents—not raw telemetry—and every response must include the teaching-only disclaimer.
