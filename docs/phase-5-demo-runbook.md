# 第五阶段演示与验收手册：受控诊断封版

本手册把第五阶段的“可复现证据”拆分为可自动验证的安全边界和在课程演示环境采集的运行记录。所有测试均只使用受控的推理摘要、离线解释制品和知识库条目；不得回放生产数据、发送 MQTT 控制命令或把任何凭据、模型文件、原始遥测写入 Git。

## 固定边界

- XGBoost 是唯一 `active` 报警源；TCN 一直是 `shadow`，不得写入 `Alarm` 或 `AlarmState`。
- `POST /api/wells/{well_id}/diagnostics` 只接受已经持久化的 `inference_id`，不接受遥测值，也不调用 MQTT。
- 每条诊断记录持久化模型、知识库和解释制品版本，以及 `evidence_status` 与 `degradation_reasons`。`complete` 代表找到了同窗口离线摘要；`degraded` 代表安全地省略特征归因；`refused` 代表没有生成事件解释。
- 性能取样和页面截图可放在 Git 忽略的 `docs/.local/phase-5/`。其中只能保存脱敏 API JSON、截图和指标，不得包含服务器地址、设备凭据、原始序列或模型制品。

## 自动验收

在仓库根目录执行：

```bash
cd apps/api && python -m pytest
cd ../web && npm run build
git diff --check
git ls-files '.env' 'ml/artifacts/*' '*.parquet' '*.pt' '*.joblib'
```

API 测试涵盖五个受控案例：Normal、Severe Slugging、Flow Instability、Hydrate in Service Line 和低置信度拒答；还涵盖缺失同窗口解释制品、移除知识条目后的拒答，以及 shadow 结果拒答。TCN 制品加载用例需要安装 `torch`；若验收机只进行 API/Web 静态回归，测试会明确标记为跳过，部署镜像仍必须安装 `torch`。

## 演示环境记录

1. 确认 `/api/models` 显示 `active / ready` 的 XGBoost 和（如制品已部署）`shadow / ready` 的 TCN，记录模型版本和时间。TCN 不可用时不得阻止 active 演示。
2. 对四类有效类别各回放一个已选、脱敏的 180 秒窗口，选中对应 active 推理结果后创建诊断。保存返回 JSON 和诊断页截图；每条均应有引用、免责声明和同窗口输入摘要。
3. 用置信度低于 `DIAGNOSTIC_MIN_CONFIDENCE` 的 active 推理创建诊断。返回必须为 `refused`，没有引用或解释制品版本。
4. 在非生产、只读制品副本中依次移除 `explanation_manifest.json` 和关联知识库条目，再创建诊断。前者应为 `completed / degraded`，且给出“不推断特征贡献”的原因；后者应为 `refused`。两次操作均不能发送 MQTT 消息，也不能新增或修改报警及报警状态。
5. 对每个场景测量诊断页首次加载、`POST /diagnostics` 和 `GET /diagnostics` 的耗时（至少三次，记录中位数和最大值），并在演示机浏览器确认页面可交互。
6. 恢复只读制品和知识库，重新执行 XGBoost 报警回归。最后检查 API 和 Web 日志中无凭据、原始数据或控制命令。

## 记录表

| 场景 | 模型/窗口/制品版本 | 引用 | 证据状态 | 拒答或降级原因 | POST / GET / 首次加载（ms） | 报警状态不变 | 复核人 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Normal |  | 是 | complete 或 degraded |  |  | 是 |  |
| Severe Slugging |  | 是 | complete 或 degraded |  |  | 是 |  |
| Flow Instability |  | 是 | complete 或 degraded |  |  | 是 |  |
| Hydrate in Service Line |  | 是 | complete 或 degraded |  |  | 是 |  |
| 低置信度 |  | 否 | refused | 置信度不足 |  | 是 |  |
| 缺失解释制品 |  | 是 | degraded | 离线摘要不可用 |  | 是 |  |
| 缺失知识条目 |  | 否 | refused | 无可引用资料 |  | 是 |  |

## 回退与封版

- 解释制品缺失时不回退到原始遥测；保留 `degraded` 审计记录并恢复只读制品即可。
- 知识条目不合格时移除条目、生成拒答记录并恢复已审阅 manifest；不得临时绕过引用要求。
- TCN 不能载入、指标不足或延迟不合格时，仅将其维持在 `shadow / unavailable`，active XGBoost、报警状态机和诊断边界不变。
- 发布前记录镜像/模型/知识库版本与 Git commit；如需回退，部署上一条已验证的主分支提交及其同版本只读制品。
