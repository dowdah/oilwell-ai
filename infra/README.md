# ECS deployment checklist

1. Install Docker Engine and Docker Compose Plugin on the Ubuntu ECS instance.
2. Copy `.env.example` to `.env` and replace every placeholder with a secret or deployment value.
3. Put `ca.crt`, `server.crt`, `server.key`, `fullchain.pem`, `privkey.pem` and the API MQTT client certificate/key under `infra/certs/`; this directory is ignored by Git.
4. Generate `infra/mosquitto/passwords` with `mosquitto_passwd`, then update `infra/mosquitto/acl` to the provisioned device IDs.
5. Configure ECS security groups to permit TCP 80/443 to the Web audience and TCP 8883 only as required for Pi connectivity. Do not publish PostgreSQL or API ports.
6. Run `docker compose -f infra/docker-compose.yml up -d --build`.

The initial compose file intentionally omits pgvector, RAG services, Redis and model training to remain viable on 2 GiB RAM.
