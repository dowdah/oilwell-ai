# 部署前提与启动顺序

本说明用于接手者搭建独立环境。现有演示系统使用版本化发布目录和固定镜像，不能把下面的构建命令直接当成生产升级脚本。2026-10-18 本地精简不连接生产服务器或树莓派，也不改动其配置。

## 目标环境

- 云端 API：Linux amd64 / Python 3.12。当前 PyTorch 依赖明确指向该平台的 CPU wheel。
- 前端构建：Node.js 22；运行时 Nginx。
- 数据库：PostgreSQL 16；消息代理：Mosquitto 2，MQTT/TLS 8883 仅走私网。
- 树莓派：独立 Edge Agent，不安装云端 PyTorch；数据目录只读，序列状态持久化。
- API/Web 分别绑定服务器回环 `127.0.0.1:8000`、`127.0.0.1:8085`；外部访问由系统 Nginx 代理。

Apple Silicon 的默认原生 API 镜像构建不能直接使用所指定的 x86_64 wheel。使用 amd64 仿真需要显式设置平台并单独验证；本项目未提供已验收的原生 ARM 云端 API 镜像。

## 独立环境所需材料

源码之外必须准备 [根目录交付清单](../README.md#外置数据模型与配置) 中的数据样例、模型制品、TLS 证书和环境配置。未配置这些材料时，仅启动容器不代表监测和推理可用。

1. 选择自己的域名与私网接入地址，建立 Edge 到云端 MQTT 的私网路径。保留 TLS 主机名校验，不开放公网 MQTT 或 PostgreSQL。
2. 在仓库根目录创建 `.env`（已有文件时不覆盖），参考 `.env.example` 替换数据库、域名、私网绑定地址及独立 API/Edge MQTT 账号。
3. 准备由受信任 CA 签发且匹配 `APP_DOMAIN` 的证书。将 broker 需要的证书与私钥放入 `infra/certs/server.crt`、`server.key`，限制私钥权限并配置更新流程。
4. 用 `mosquitto_passwd` 创建受限的 `infra/mosquitto/passwords` 文件，账号与 `infra/mosquitto/acl` 一致。该路径和证书目录均被 Git/Docker 构建上下文忽略。
5. TLS 环境将 API 的 `MQTT_HOST` 设置为证书域名（通常等于 `APP_DOMAIN`），而非示例中的 `mosquitto`。Compose 会为 broker 设置域名网络别名。设置 `MQTT_BIND_IP` 为本机实际拥有的私网地址。
6. 将已验证制品放入 `ml/artifacts/current`、`tcn-shadow`、`explanations`。核对元数据、文件哈希和只读挂载；不要部署被否决的 Phase B 二分类候选。
7. 从源码根目录运行：

```bash
# 仅首次创建时复制；填妥配置后再启动。
test -f .env || cp .env.example .env
docker compose --env-file .env -f infra/docker-compose.yml up -d --build
```

## 网页入口

Compose Web 容器只提供静态资源，不自行代理 API。完整部署需要按 `nginx/default.conf.template` 配置系统 Nginx：`/` 指向 Web，`/api/` 指向 API，`/ws` 保留 WebSocket Upgrade 头。系统 Nginx 管理对外 443 和自己的证书路径。

开发环境可在 API 可通过开发机 `localhost:8000` 访问时运行 `apps/web` 的 `npm run dev`，Vite 已代理 `/api` 与 `/ws`。仅打开 8085 静态端口不能当作完整应用验收。

证书签发方式根据端口与 DNS 管理条件选择。`bootstrap.conf.template` 仅适用于系统 Nginx 可占用 80 的环境；手工 DNS-01 证书不会自动续期，必须安排人工更新或独立配置自动续期。不要覆盖同机其他站点或服务。

## 树莓派 Edge

在 `services/edge-agent/` 创建独立 `.env`：账号与 ACL 一致，`MQTT_HOST` 使用证书域名，`MQTT_CONNECT_IP` 为私网 broker 地址，`EDGE_DATA_HOST_DIR` 指向合规 Parquet 样例所在目录。保持 `EDGE_REPLAY_AUTOSTART=false`。

在该目录运行：

```bash
docker compose --env-file .env -f docker-compose.yml up -d --build
```

页面出现 ONLINE 心跳后，再加载实例、设置速度和开始回放。`/state` 序列文件用于避免重启后重复序列；不得删除已有状态卷或同时启动同一设备的多个写入进程。

## 完成条件与接手边界

逐项检查模型 ready、心跳、命令回执、完整推理窗口、历史入库、WebSocket 与浏览器页面；参考 [使用说明](../docs/final/user-guide-and-demo.md) 和 [评估与限制](../docs/final/evaluation-and-limitations.md)。基础部署不要求外部 LLM；需要时按 [DeepSeek 接入说明](../docs/final/deepseek-setup.md) 独立配置并联调。

2026-10-17 只读复查记录的生产 API 源码入口为 `/opt/oilwell-ai/current-release/source`，顶层旧源码不能用于重建。生产维护前应重新确认实际发布目录、环境配置和回退条件；本次本地清理不检查或更改服务器备份。源码包不含真实配置或运维凭据，本地历史恢复包已从交付工作区清除。
