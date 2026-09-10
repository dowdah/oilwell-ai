# OilWell AI

> 基于边云协同、多变量时序学习与 RAG 的油井异常监测与智能辅助诊断系统。

本仓库实现《石化智能信息系统工程》课程项目的端到端 MVP：树莓派回放 Petrobras 3W Dataset，使用 MQTT 上传遥测数据，云端保存、告警并经 WebSocket 驱动实时可视化。

## 架构

```text
3W Parquet → Raspberry Pi Edge Agent → MQTT/TLS → FastAPI → PostgreSQL
                                                      ├─ WebSocket → Vue 3
                                                      └─ Alarm / model adapter
```

- **边缘端**：Pi 4B 以批处理方式读取 Parquet，支持 1×、5×、10×、20× 回放、心跳和云端控制。
- **云端**：针对 2 vCPU / 2 GiB ECS 的轻量 Docker Compose（Nginx、API、PostgreSQL、Mosquitto）。训练与完整原始数据不进入 ECS。
- **模型路线**：MVP 后在 Mac 上完成 Isolation Forest、XGBoost、TCN；云端仅加载推理制品。

## 数据契约

默认窗口为 180 秒，固定 7 个变量：`P_PDG`、`P_TPT`、`T_TPT`、`P_MON_CKP`、`T_JUS_CKP`、`P_JUS_CKGL`、`QGL`。

MQTT topic：

```text
3w/edge/{device_id}/telemetry
3w/edge/{device_id}/status
3w/edge/{device_id}/command
3w/well/{well_id}/alarm
```

完整 3W 数据、模型制品、证书、密码、API Key 和服务器地址不得提交。按 instance 或 well 分组划分训练、验证和测试集，禁止随机打散时间点。

## 本地启动

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
cd apps/web && npm install && npm run dev
```

API 文档位于 `http://localhost:8000/docs`。生产环境由 Nginx 公开 HTTPS Web；Pi 的 MQTT TLS 经 WireGuard 等私网覆盖网络进入 ECS，避免因动态公网 IP 或 CGNAT 依赖 MQTT 公网入口。部署前需准备域名、证书、MQTT 凭据和私网端点配置。

## 验证

```bash
cd apps/api && python -m pytest
cd apps/web && npm run build
```

## 安全与免责声明

MQTT 禁止匿名访问，使用独立设备凭据、TLS、topic ACL 与私网覆盖网络。AI 输出仅用于辅助分析与教学演示，**不构成实际油井控制指令或生产操作依据**。

## License

[MIT](LICENSE)
