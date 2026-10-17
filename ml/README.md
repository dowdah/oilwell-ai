# 训练、数据与制品说明

本目录保留完整离线训练和评估工具，运行 API 同时依赖 `oilwell_ml` 中的 TCN 架构、特征与标准化契约。训练在独立开发机完成，不在 ECS 或树莓派执行。日常使用和课程演示不需要重新训练。

2026-10-18 交付精简后，本地只保留四个演示样例、当前 XGBoost / TCN 与解释制品；完整研究数据和旧候选制品已清除。历史审计的 **55 个实例**及旧 **187-instance** 选择不是当前库存；四个演示样例不能替代完整分组训练集。重新训练需重新取得相应数据，核对文件哈希和协议，且不能把被否决二分类候选替换到 active。

## 1. 数据来源与保留资产

源数据为 Petrobras 3W。上游 URL、原始提交号、四个样例与九个制品的路径、版本和 SHA-256 见 [演示资产清单](../docs/experiments/demo-assets.json)；本地 `ml/data/raw/petrobras-3w/` 保留提取自上游提交的数据许可 `dataset/LICENSE-CC-BY`（CC BY 4.0）、上游代码许可 `LICENSE.md` 与引用说明 `CITATION.md`。数据许可和引用要求独立于项目源码的 MIT 许可证。

下载工具要求显式、获准的来源 URL，输出只能位于忽略目录 `ml/data/raw/`。它校验可选的 SHA-256，但不会自动解压，也不会替代来源与许可审查。获取数据后记录版本和引用，不将原始文件提交 Git 或上传 ECS。

```bash
python scripts/download_3w.py --source-url '<authorized dataset archive URL>' \
  --output ml/data/raw/research-dataset.zip --sha256 '<expected archive SHA-256>'
```

取得数据后按上游格式解压至独立的忽略目录，以下命令中的 `/absolute/path/to/complete-3w-dataset` 需替换成该目录。保留原有八份 JSON 不变：四分类 manifest、selection、EDA、split 位于 `docs/experiments/`，二分类 audit、selection、split、protocol 位于 `docs/phase-b/`。它们保存历史实验，而非自动发现的当前文件清单。

## 2. 依赖与实验约束

可创建新的开发虚拟环境并安装 `ml/requirements.txt`。交付包不含 `.venv` 或缓存，API 的 Linux amd64 依赖与本地训练环境不同，按实际平台安装并验证。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r ml/requirements.txt
```

- 固定七个核心变量、180 秒窗口，现有训练默认步长 10 秒；使用 instance / well 分组，不随机切单个采样点。
- 首轮四类为 Normal、Severe Slugging、Flow Instability、Hydrate in Service Line。
- 基线工具保留 Isolation Forest、二分类 XGBoost 和四分类 XGBoost，随后训练 TCN shadow；这些入口存在不代表所有模型已部署。
- 报告 Precision、Recall、Macro F1、混淆矩阵和 CPU 延迟；候选、阈值与标准化不得使用测试组调优。
- 模型发布需符合 `model_metadata.schema.json`，记录数据版本、Git 提交和输入清单哈希；发布与生产替换是单独的维护工作。

下面的示例将新输出放入忽略的研究目录，不覆盖保留协议或当前演示模型。四分类基线脚本会生成自己的 split；TCN 必须复用同一次 split。

## 3. 数据检查、四分类与 TCN

```bash
mkdir -p ml/artifacts/research-docs
python ml/scripts/inspect_3w.py /absolute/path/to/complete-3w-dataset \
  --output ml/artifacts/research-docs/3w-manifest.json
python ml/scripts/select_instances.py ml/artifacts/research-docs/3w-manifest.json \
  --output ml/artifacts/research-docs/3w-instance-selection.json
python ml/scripts/report_eda.py ml/artifacts/research-docs/3w-manifest.json \
  ml/artifacts/research-docs/3w-instance-selection.json \
  --data-root /absolute/path/to/complete-3w-dataset \
  --output-dir ml/artifacts/research-docs
python ml/scripts/train_baselines.py ml/artifacts/research-docs/3w-instance-selection.json \
  --data-root /absolute/path/to/complete-3w-dataset \
  --split-output ml/artifacts/research-docs/3w-split.json \
  --artifacts ml/artifacts/retrained-baselines
python ml/scripts/train_tcn.py ml/artifacts/research-docs/3w-instance-selection.json \
  --data-root /absolute/path/to/complete-3w-dataset \
  --split ml/artifacts/research-docs/3w-split.json \
  --xgb-metrics ml/artifacts/retrained-baselines/metrics.json \
  --artifacts ml/artifacts/retrained-tcn
```

这些是重新研究的命令，不保证复现已验收制品。四分类选择按实例目录标签确定目标，仅从连续且完整的目标标记行生成窗口。Dataset 2.0.0 对瞬态使用“事件标签 + 100”，例如水合物 `9` 可含 `109`；不能将文件中的 Normal 段当成水合物。

TCN 流式读取 Parquet，标准化参数只由训练组拟合，输出 `tcn_model.pt`、`tcn_config.json`、`scaler.json`、`model_metadata.json` 和 `comparison.json`。当前保留的 `ml/artifacts/current/metrics.json` 是 TCN 比较流程的输入，因此不是冗余文件。线上 shadow 不参与报警或控制。

## 4. 二分类审计、冻结与候选工具

[评估与限制](../docs/final/evaluation-and-limitations.md) 保留冻结井划分、55 个实例审计和 held-out WELL-00014 的最终结论：唯一候选异常召回约 2.49%、F1 约 4.85%，**rejected / never deployed**。不能将旧 187-instance 选择或未复现 C2 结果当成当前能力。

| 工具 | 用途与输入 |
| --- | --- |
| `scripts/audit_available_binary_data.py` | 对显式提供的历史 selection 和数据根重新审计；不自行搜索缺失源文件 |
| `scripts/freeze_available_binary_split.py` | 从 audit 和 selection 生成固定井级 split 与 protocol |
| `ml/scripts/train_binary_candidate.py` | 按冻结协议训练并用 validation 选阈值，默认不读取 test 窗口 |
| `scripts/select_phase_b_candidate.py` | 从候选报告选择 validation 候选，输出到忽略目录 |

两个审计工具的 Markdown 默认写入 `ml/artifacts/research-docs/`；其 JSON 默认路径仍是历史协议位置。新研究必须显式指定新的 JSON 输出，避免覆盖已冻结记录。例如已有获准历史 selection 时：

```bash
python scripts/audit_available_binary_data.py /absolute/path/to/historical-selection.json \
  --data-root /absolute/path/to/complete-3w-dataset \
  --selection-output ml/artifacts/research-docs/binary-selection.json \
  --audit-json ml/artifacts/research-docs/binary-audit.json
python scripts/freeze_available_binary_split.py \
  --audit ml/artifacts/research-docs/binary-audit.json \
  --selection ml/artifacts/research-docs/binary-selection.json \
  --split-output ml/artifacts/research-docs/binary-split.json \
  --protocol-output ml/artifacts/research-docs/binary-protocol.json
```

重现已冻结 55-instance 协议时应直接使用保存的 selection/split，并先复制 protocol，因为训练脚本会更新传入 protocol 中的窗口计数。确认完整源数据与哈希匹配后，才运行：

```bash
mkdir -p ml/artifacts/research-docs
cp docs/phase-b/frozen/protocol.json ml/artifacts/research-docs/phase-b-protocol.json
python ml/scripts/train_binary_candidate.py \
  --selection docs/phase-b/frozen/selection.json \
  --split docs/phase-b/frozen/split.json \
  --protocol ml/artifacts/research-docs/phase-b-protocol.json \
  --data-root /absolute/path/to/complete-3w-dataset \
  --candidate baseline \
  --artifact-dir ml/artifacts/retrained-binary \
  --report ml/artifacts/research-docs/binary-report.json
```

原实验已对 test 评估一次并结束；以上示例不带 `--evaluate-test`。若开展独立复现，应明确其复现目的，不利用已有测试结果继续挑选候选或阈值。课程演示无需执行这些命令。

## 5. 离线解释与验证

2026-10-18 已修复井标识缺失并重建本地四条解释。准备脚本从与 Edge 相同的 `WELL-xxxxx_*.parquet` 文件名恢复井 ID；显式声明冲突或无法确定身份时拒绝生成。每个样例取首个完整的 180 行连续 1 Hz 回放窗口（首末跨度 179 秒），不按事件标签重新起算窗口，因此与 API 首次预测对齐。训练流程原有的指定标签筛选不变，样例类别也不保证首窗口的模型预测类别。

下列命令只需现存四个样例和当前 XGBoost，不需要重新训练或取得完整研究集。生成的私有特征窗口不进入 Git，示例解释写入新目录以免直接替换已交付制品：

```bash
python ml/scripts/prepare_demo_windows.py docs/experiments/3w-instance-selection.json \
  --data-root ml/data/raw/petrobras-3w/dataset \
  --output ml/data/raw/demo-windows.json
python ml/scripts/generate_explanations.py \
  --model-dir ml/artifacts/current \
  --windows-json ml/data/raw/demo-windows.json \
  --output ml/artifacts/retrained-explanations/explanation_manifest.json
```

生成器要求非空 `well_id`、带时区且符合模型行数的首末时间、有限特征值；输出时间统一为 UTC。manifest 只保存井与窗口标识、贡献排名/数值、趋势摘要及模型元数据，不含原始行或输入特征值。审阅并验证井、模型版本、特征模式及首末时间全部匹配后，才可替换独立实例的解释文件，并同步更新资产清单的版本、大小与 SHA-256。

本地制品 `xgb-shap-20261017T210806Z` 仅覆盖 [使用说明列出的四个窗口](../docs/final/user-guide-and-demo.md#本地修复版的-shap-覆盖窗口)，不覆盖后续每 10 秒产生的新预测。API 仍只读取只读 manifest，匹配失败继续降级，不能跨井或跨窗口复用解释。此次没有更新生产制品或报告 31；上述流程也不自动部署。

运行 `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=ml python -m pytest ml/tests -q` 检查特征、分组、窗口、解释及 TCN 契约；单线程设置避免本机数值库的 OpenMP 同步停滞。推理一致性应使用相同样例窗口比较加载结果与分数；测试通过不代表重新训练模型已达到泛化要求。
