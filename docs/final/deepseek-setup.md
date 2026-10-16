# DeepSeek V4.1 接入说明

文档更新：2026-10-17。适用于 OilWell AI 的辅助诊断模块。真实供应商联调发生于 2026-09-22；10-17 仅做本地测试与生产只读复查。

## 模型与接口

本部署使用 `deepseek-flash`。2026-09-22 联调时，按官方文档核对其对应 DeepSeek-V4.1-Flash；供应商可能更新模型别名，后续更换或重新部署时应重新核对。不要把聊天产品显示名称直接写成模型 ID。

- Base URL：`https://api.deepseek.com`
- 请求地址：`https://api.deepseek.com/chat/completions`
- 配置 Provider：`deepseek`
- 模型 ID：`deepseek-flash`

依据：[官方更新日志](https://api-docs.deepseek.com/updates/)、[Chat Completions 接口文档](https://api-docs.deepseek.com/api/create-chat-completion/)。供应商日后调整别名时需要重新核对。

## 当前接入状态

2026-09-22 已配置 API Key 并启用生产 DeepSeek 接入。模型列表查询返回 200，`deepseek-flash` 可用；不含油井数据的一次真实 JSON 协议请求返回 200，约 1.38 秒完成，使用 348 tokens（输入 229、输出 119）。密钥未显示在日志或文档中。

生产 API 容器已切换为 `infra-api-deepseek-20260922`，模型为 `deepseek-flash`，关闭思考模式，输出上限 2048 tokens，HTTP 超时 30 秒。Web、树莓派、数据库及模型制品沿用原配置。

用户明确授权后，已通过生产浏览器完成一次真实油井窗口诊断验收：选择 WELL-00014、窗口 `2016-03-04 16:21:16–16:24:15 UTC`（active 推理 ID 8631），生成并保存报告 **31**，时间为 `2026-09-22 09:28:31 UTC`（北京时间 17:28:31）。数据库审计记录确认 `llm.provider=deepseek`、`llm.model=deepseek-flash`、`llm.status=completed`，报告不含 `LLM analysis unavailable`。

报告包含七变量统计、实验性模型提示、人工核查建议及三个本次知识库引用。证据状态仍为“安全降级”，唯一原因是缺少同窗口离线 SHAP 摘要；LLM 调用本身成功。系统健康正常，既有报警未被确认或修改。真实调用发生一次，先前被自动审批拦截的点击没有执行。

生产使用镜像 `oilwell-ai-api:359f10a-deepseek`；部署前该镜像的 API 测试为 **53 passed**，包含隔离 PostgreSQL 上的 9 项集成测试和新增 DeepSeek 请求/降级测试。自动化外部请求测试使用模拟传输；上述连接预检和报告 31 则是另外完成的真实供应商调用。

2026-10-17 只读复查确认，服务器 API 发布目录仍为 `/opt/oilwell-ai/releases/359f10a-deepseek-20260922`，`/opt/oilwell-ai/current-release` 指向该目录。当时基于 `359f10a` 构建的适配现已收齐到 `main` / `codex/final-delivery` 的交付提交；生产镜像仍沿用原标签，本次不重新部署。源码精确版本以交付分支提交为准。

本次复查确认配置启用、保存的报告 31 可读；没有再次调用供应商，也不据此断言当前余额或外部 API 可用性。交付收尾本地 API 测试为 44 passed、9 skipped，数据库完整测试记录仍是上述 9 月 22 日的结果，见 [测试矩阵](test-matrix.md)。

服务器 `/opt/oilwell-ai/llm.env` 已按权限 `600` 创建，内容结构如下：

```dotenv
DIAGNOSTIC_LLM_ENABLED=true
DIAGNOSTIC_LLM_PROVIDER=deepseek
DIAGNOSTIC_LLM_BASE_URL=https://api.deepseek.com
DIAGNOSTIC_LLM_API_KEY=
DIAGNOSTIC_LLM_MODEL=deepseek-flash
DIAGNOSTIC_LLM_TIMEOUT_SECONDS=30
DIAGNOSTIC_LLM_MAX_OUTPUT_TOKENS=2048
```

上面留空的密钥仅为文档示例，真实密钥已在服务器配置并注入当前 API 容器。更换密钥时请仅在服务器上修改，不要把密钥放进 Git、聊天、PPT 或截图。DeepSeek 聊天网页账号本身不能代替 API Key。

服务器已提供隐藏输入脚本。通过已有 SSH 连接登录服务器后执行：

```bash
python3 /opt/oilwell-ai/set-deepseek-key.py
```

粘贴密钥时终端不会回显；回车后脚本将其写入权限为 `600` 的环境文件。它不会启动服务或发送外部请求。

## 接通步骤

1. 在 DeepSeek 官方 API 平台创建或取得有可用额度的 API Key。
2. 在服务器受限环境文件中填入密钥，保持其他配置不变。
3. 使用候选镜像和该环境文件进行一次模型列表检查与小规模接口联调。检查模型存在、JSON 协议有效，而不把失败结果当成模型分析成功。
4. 保留原容器配置和回退路径，用现有运行镜像的 DeepSeek 适配版本重建 API 容器，并注入原环境配置与新增 LLM 配置。无需更新 Web、数据库或树莓派。
5. 从“辅助诊断”选择已有完整 active 推理，生成一条新报告，确认报告与数据库审计记录均成功。

仅修改环境文件后执行 `docker restart` 不会更新现有容器的环境变量。当前生产采用版本化发布目录和镜像；不要在旧的 `/opt/oilwell-ai/apps` 源码上直接执行构建。

## 已适配的请求行为

- 使用 DeepSeek 支持的 `system` 消息角色。
- 关闭思考模式：`thinking.type=disabled`，用于交互式课程演示。
- 使用 `response_format.type=json_object`，并在提示中给出六字段 JSON 格式。
- 非流式返回，生成上限 2048 tokens，HTTP 超时配置 30 秒，不自动重试付费请求。
- JSON 字段不完整、返回被截断、认证失败、限流或超时时，保留模板与真实检索引用。
- 成功报告的审计输入中记录 `llm.provider`、`llm.model` 和 `llm.status=completed`，不记录密钥。
- LLM 成功不等于证据齐全：如果缺少同窗口离线 SHAP，仍保留相应降级状态。

## 如何判断调用成功

新报告不再因 LLM 不可用而显示 `LLM analysis unavailable`，数据库中相应诊断的 `input_summary.llm` 记录 `deepseek / deepseek-flash / completed`。报告可能仍因缺少 SHAP 而显示“安全降级”，这不等于 LLM 调用失败。

生成一条新的记录进行验证；系统不会重新生成以前保存的模板报告。页面没有通用聊天输入框，外部模型仅在合格诊断请求中调用。

## 数据与边界

外部请求包含井和窗口标识、模型结果、七变量统计、报警摘要及检索资料的引用元数据，不包含完整原始时序、MQTT/数据库凭据或控制命令。当前实现不会向外部模型传送知识条目的全文，也不是文档上传或向量数据库检索系统。

引用列表由系统生成，模型文本仍需人工核验；不能仅凭提示词把输出视为可靠的现场操作建议。此接入不改变被否决二分类研究模型的状态。

启用会产生供应商 API 调用费用。当前适配限制单次输出量，但不提供全站每日费用上限；公开诊断入口的访问控制、限流与供应商用量限制应按实际使用范围管理。
