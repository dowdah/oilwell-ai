# 第四阶段演示手册：可解释诊断与受控 RAG

## 演示前置条件

- 第三阶段 active XGBoost 和 shadow TCN 均按 `docs/phase-3-demo-runbook.md` 验证；TCN 仍为 shadow，且其指标、延迟和同窗口对照证据可查。
- 仅在训练机上针对脱敏的离线特征窗口运行 `ml/scripts/generate_explanations.py`。将得到的 `explanation_manifest.json` 放到 Git 忽略的 `ml/artifacts/explanations/`；文件包含模型版本、特征 schema、窗口时间、全局重要性及窗口摘要，不包含原始时序。
- API 将该目录只读挂载为 `/models/explanations`。知识资料由 `docs/knowledge-base/manifest.json` 管理，每条都有来源、版本、许可与教学摘要。

## 演示步骤与验收

1. 打开“模型中心”，选择已完成 180 秒窗口的油井，确认 active XGBoost 与 shadow TCN 的 telemetry ID 相同。只有 active 的结论可用于诊断。
2. 打开“辅助诊断”，选择 active 结果并生成记录。页面显示模型版本、窗口、SHAP 摘要（若该窗口制品存在）、shadow 对照、资料引用和记录 ID。
3. 验证诊断文字含引用、置信边界/拒答说明、缺失信息和“仅教学辅助，不构成操作指令”提示；当置信度低、非 active 结果或缺少可引用资料时必须显示拒答。
4. 调用 `GET /api/wells/{well_id}/diagnostics`，保存无秘密的结果截图或 JSON。记录应含请求时间、模型版本、知识库版本、解释制品版本和输入摘要；输入摘要不得出现完整遥测数据。
5. 回放 Normal、Severe Slugging、Flow Instability、Hydrate in Service Line 以及一个低置信度案例，人工记录事实性、引用覆盖、拒答行为和页面响应时间，填入下方评估表。
6. 重新执行第三阶段 active XGBoost 报警回归测试。诊断 API 不发布 MQTT 命令，且不写入 `Alarm` 或 `AlarmState`；TCN 始终不能升级为 active。

| 场景 | 模型/窗口可追溯 | 至少一条引用 | 拒答或不确定信息 | 页面可交互 | 复核人 |
|---|---|---|---|---|---|
| Normal |  |  |  |  |  |
| Severe Slugging |  |  |  |  |  |
| Flow Instability |  |  |  |  |  |
| Hydrate in Service Line |  |  |  |  |  |
| 低置信度 |  | N/A（拒答） |  |  |  |

## 回退

移除或修复只读解释制品后重启 API；诊断将报告缺少 SHAP 摘要而不会回退到原始遥测。若知识库审阅失败，删除相应资料条目并重新部署。无论哪种情况，active XGBoost 报警闭环保持不变。
