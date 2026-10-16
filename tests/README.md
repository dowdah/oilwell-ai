# 验证与课程验收

结果按执行日期记录在 [测试矩阵](../docs/final/test-matrix.md)。以下命令在依赖已经安装的独立开发环境中执行，不连接生产数据库。

```bash
PYTHONPATH=apps/api python -m pytest apps/api/tests -q
PYTHONPATH=services/edge-agent python -m pytest services/edge-agent/tests -q
PYTHONPATH=ml python -m pytest ml/tests -q
cd apps/web && npm ci && npm run build
```

## 数据库集成测试

API 的 9 项数据库测试只接受主机 `127.0.0.1`、数据库名 `oilwell_test`；缺少配置时跳过。先在本机独立 PostgreSQL 16 中准备该数据库和测试用户，再通过 `OILWELL_TEST_DATABASE_URL` 配置 `postgresql+asyncpg://测试用户:测试密码@127.0.0.1:端口/oilwell_test`。密码仅放本地受限环境配置，不提交、不写入日志；URL 不带 `sslmode`。

测试按唯一 schema 创建数据并在结束后移除该测试 schema。必须使用专用测试库，不能将生产实例转发到该地址来绕过保护。

## 运行验收

1. 由维护人员准备部署环境、证书、模型与合规数据样例，按 [部署说明](../infra/README.md) 启动独立环境。
2. 验证边缘心跳、命令回执、遥测持久化、WebSocket 更新和完整窗口的 active/shadow 结果。
3. 根据 active 的实际连续窗口结果检查报警规则；数据实例标签不能保证模型必然识别异常。确认报警的操作会修改保存状态。
4. 检查诊断引用、实验性标签、LLM 失败降级和证据不足拒答。自动化测试使用模拟外部接口；真实 LLM 请求另需配置、数据使用授权和费用预算。
5. MQTT 断连、恢复和备份恢复等故障演练仅在隔离环境或另行授权的维护窗口执行。

课程现场按 [完整使用与演示说明](../docs/final/user-guide-and-demo.md) 操作，不把故障演练作为日常演示前置步骤。
