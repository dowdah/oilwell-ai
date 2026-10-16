# 课程项目交付清单

整理日期：2026-10-17。课程：《石化信息工程》。项目：OilWell AI 边云协同油井监测与知识增强辅助分析系统。

## 版本与入口

最终交付分支为 `codex/final-delivery`，与本次收尾后的 `main` 指向同一提交。精确版本以 `git rev-parse HEAD` 或下载包对应的 Git 提交为准；交付分支已纳入 DeepSeek 适配、测试与两份使用/接入说明。

现有生产镜像是在 2026-09-22 基于 `359f10a` 加 DeepSeek 适配构建的。本次将该适配收齐进 Git 并统一文档，不重新部署、不改动生产配置；生产镜像标签仍保留原来的名称。

| 读者任务 | 阅读入口 |
| --- | --- |
| 快速了解成果与启动前提 | [README](../../README.md) |
| 逐页使用、准备现场演示、处理常见问题 | [完整使用与演示说明](user-guide-and-demo.md) |
| 8～10 分钟现场讲述 | [简版演示脚本](demo-script.md) |
| 理解架构与数据边界 | [系统架构](system-architecture.md) |
| 确认测试覆盖与未验证项目 | [测试矩阵](test-matrix.md) |
| 接入或维护 DeepSeek | [DeepSeek 接入说明](deepseek-setup.md) |
| 理解模型研究结论 | [限制说明](limitations.md)、[Phase B 报告](../phase-b/final-report.md) |
| 搭建独立实例 | [部署前提与顺序](../../infra/README.md) |

## 源码包包含

- `apps/api/`、`apps/web/`：后端、前端和测试。
- `services/edge-agent/`：数据回放、持久化序列、单写者保护与测试。
- `infra/`：部署示例、MQTT ACL 与 Nginx 模板，不含真实密码或证书。
- `ml/`、`scripts/`：离线研究、数据审计和制品准备工具；不要求演示时训练。
- `docs/final/`：交付说明；`docs/knowledge-base/`：经审阅的知识条目。
- `docs/experiments/`、`docs/phase-b/`：实验选择、分组与拒绝部署结论的可追溯依据。
- `.env.example`、许可证与依赖锁文件。

旧阶段规划、迁移过程副本与候选过程文件已在基础提交 `359f10a` 中精简，本次交付分支沿用这一结果。旧提交仍可从 Git 历史和本地恢复包取回。不会删除数据、模型或把被否决研究改写成上线能力。

## 源码之外需要单独准备的材料

| 材料 | 放置方式 / 获取要求 | 缺失时的影响 |
| --- | --- | --- |
| 合规 3W Parquet 样例 | 从获准数据源获取，记录来源、版本和许可；以 `EDGE_DATA_HOST_DIR` 只读挂载到 Edge `/data` | 无法回放；新数据库中没有演示历史 |
| 活动 XGBoost | `ml/artifacts/current/model_metadata.json` 及其声明的 `artifact_file`；已验证部署为 `xgboost_model.json`、版本 `xgb-20260912T082447Z` | active 推理不可用，不可宣称具备模型报警能力 |
| TCN shadow | `ml/artifacts/tcn-shadow/` 中的 `model_metadata.json`、`tcn_model.pt`、`tcn_config.json`、`scaler.json` | 无 shadow 对照，不应替换 active |
| 同窗口离线解释 | `ml/artifacts/explanations/explanation_manifest.json`，模型版本、井和窗口匹配；额外制品按 manifest 需要提供 | 报告保留统计与引用，但解释证据降级 |
| 数据库、MQTT、TLS 配置 | 接手者自行创建受限 `.env`、账号、ACL、证书；遵守私网绑定与主机名校验 | 链路不能正常建立 |
| DeepSeek API Key | 可选；自行申请并写入受限环境文件，默认不开启外部调用 | 保留模板报告，不影响监测主链路 |
| 已有演示记录与录像 | 现场可访问已有演示系统，或使用预先保存的合规截图/录像；不随源码传播生产数据库 | 新实例没有报告 31，需自行完成获准的数据回放与诊断 |

模型二进制可由项目维护者按许可和传输约定另行提供，交接时应附 SHA-256 清单并核对元数据；本次提交不上传、不删除这些文件。重新训练得到的制品不应假设与已验证版本相同。原始数据来源与当前本地覆盖见 [数据审计](../phase-b/available-data-audit.md)。

## 提交与打包方式

课程源码优先提供交付分支链接或该分支的 Git archive。不要直接压缩整个开发目录；其中可能包含 `.env`、证书、数据库备份、数据集、模型、虚拟环境与依赖缓存。

```bash
# 在仓库根目录运行，输出到仓库外；提交后再执行。
git archive --format=zip --output=../oilwell-ai-course-delivery.zip codex/final-delivery
```

此压缩包只包含受版本控制文件，不含 Git 历史和外置材料。不要用 `git clean -fdx` 来准备交付包；也不要通过清空数据或删除模型来“精简”。

课设书面报告、PPT 和演示录像是否必须提交，以教师要求为准。本仓库提供的是系统、使用文档及实验依据，不把尚未制作的 PPT/录像计入已交付材料。

## 验证范围

2026-10-17 本地 API 44 passed / 9 skipped，Edge 16 passed，ML 17 passed，Web 构建通过。2026-09-22 的 DeepSeek 适配镜像曾通过完整 53 项 API 测试并完成真实报告 31。不同日期、环境的结果不能合并为一次全量验收，详见 [测试矩阵](test-matrix.md)。

交付收尾不再次启动回放、不发出供应商请求、不更改报警、不改动生产服务。部署可访问和历史报告存在不等于当前新请求、余额或长时间稳定性已重新验收。
