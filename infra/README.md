# ECS deployment checklist

1. The ECS already runs system Nginx and Certbot. Leave those processes in control of TCP 80/443; Compose publishes the API and Web only to `127.0.0.1:8000` and `127.0.0.1:8085`.
2. Copy `.env.example` to `.env` and replace every placeholder with a secret or deployment value.
3. Provision `oil-well-ai-demo.dowdah.com` in Cloudflare as an unproxied A record to the ECS public address. This ECS has an existing Docker service on TCP 80, so issue the certificate with Certbot DNS-01 (`certbot certonly --manual --preferred-challenges dns -d oil-well-ai-demo.dowdah.com`) and install only the rendered HTTPS `default.conf.template`. The included `bootstrap.conf.template` is for environments where system Nginx owns TCP 80.
4. Copy that certificate and private key into ignored `infra/certs/` as `server.crt` and `server.key`. The API and Pi use their normal system trust stores to validate Let’s Encrypt; the Mosquitto broker presents this certificate.
5. Generate `infra/mosquitto/passwords` with `mosquitto_passwd`, then update `infra/mosquitto/acl` to the provisioned device IDs. For a TLS deployment, set the API's `MQTT_HOST` to `APP_DOMAIN`; Compose assigns that name as an internal broker alias so hostname verification remains enabled.
6. Configure ECS security groups to permit TCP 80/443 to the Web audience and TCP 8883 only as required for Pi connectivity. Do not publish PostgreSQL or API ports.
7. Run `docker compose -f infra/docker-compose.yml up -d --build`. On an image-preloaded production host, use `--no-build`.

The initial compose file intentionally omits pgvector, RAG services, Redis and model training to remain viable on 2 GiB RAM.

Manual DNS-01 certificates do not renew automatically. Before expiration, repeat the DNS challenge and refresh the copied MQTT certificate/key, or replace the manual flow with a scoped Cloudflare DNS API token and Certbot DNS plugin.
