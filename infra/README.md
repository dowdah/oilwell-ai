# ECS deployment checklist

1. The ECS already runs system Nginx and Certbot. Leave those processes in control of TCP 80/443; Compose publishes the API and Web only to `127.0.0.1:8000` and `127.0.0.1:8085`.
2. Copy `.env.example` to `.env` and replace every placeholder with a secret or deployment value.
3. Provision `oil-well-ai-demo.dowdah.com` in Cloudflare as an unproxied A record to the ECS public address. First install and enable the rendered `bootstrap.conf.template`; after `nginx -t`, issue a certificate with `certbot certonly --webroot -w /var/www/certbot -d oil-well-ai-demo.dowdah.com`. Replace the bootstrap file with the rendered `default.conf.template`, test and reload Nginx.
4. Copy that certificate and private key into ignored `infra/certs/` as `server.crt` and `server.key`. The API and Pi use their normal system trust stores to validate Let’s Encrypt; the Mosquitto broker presents this certificate.
5. Generate `infra/mosquitto/passwords` with `mosquitto_passwd`, then update `infra/mosquitto/acl` to the provisioned device IDs.
6. Configure ECS security groups to permit TCP 80/443 to the Web audience and TCP 8883 only as required for Pi connectivity. Do not publish PostgreSQL or API ports.
7. Run `docker compose -f infra/docker-compose.yml up -d --build`.

The initial compose file intentionally omits pgvector, RAG services, Redis and model training to remain viable on 2 GiB RAM.
