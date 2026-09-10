# 基于边云协同、多变量时序学习与RAG的油井异常监测与智能辅助诊断系统

> 面向课程《石化智能信息系统工程》的学期项目总说明 / Codex 启动项目上下文
>
> 目标：完成一个可运行、可部署、可答辩、可通过 Git 仓库提交的端到端石油工业智能信息系统原型。

---

## 1. 项目背景

### 1.1 课程与个人条件

- 专业：计算机科学与技术，大四。
- 课程：石化智能信息系统工程。
- 交付形式：系统 + 源代码 + 答辩 + PPT，以 Git 仓库形式提交。
- 项目周期：1 个学期，目前处于第 2 周。
- 已有经验：Python Flask + Vue3 网站开发。
- 期望：技术路线贴合行业发展趋势，并能应用 AI 技术。

### 1.2 现有硬件资源

- 开发/训练工作站：MacBook Pro 14-inch 2021，MacBookPro18,3，Apple M1 Pro，16 GB Unified Memory。
- 边缘设备：Raspberry Pi 4B，2 GB RAM。
- 生产服务器：阿里云 ECS，2 vCPU / 2 GiB RAM / 100 Mbps。
- 可选资源：如后续确有需要，可临时租用云 GPU；但项目设计不得依赖 GPU 才能运行。

---

## 2. 推荐正式题目

### 2.1 推荐中文题目

**基于边云协同、多变量时序学习与RAG的油井异常监测与智能辅助诊断系统设计**

### 2.2 可选简化题目

**基于边云协同与多变量时序智能的油井异常监测与辅助诊断系统设计**

### 2.3 英文题目

**Intelligent Oil Well Anomaly Monitoring and Decision Support System Based on Edge-Cloud Collaboration, Multivariate Time-Series Learning and RAG**

---

## 3. 项目定位

本项目不是单纯的：

- Jupyter Notebook 中的故障分类实验；
- Vue3 管理系统；
- 大模型聊天页面；
- 纯 RAG 问答系统。

而是将以下技术整合成一套可运行的信息系统：

```text
IoT / MQTT
+ Edge Computing
+ Cloud Backend
+ Multivariate Time-Series AI
+ Explainable AI
+ RAG / LLM
+ Web Visualization
```

核心价值是：

> 将公开工业数据、边缘采集、云端信息系统、工业时序 AI、可解释诊断和生成式 AI 组合成完整的端到端工业智能信息系统原型。

---

## 4. 数据集选择：Petrobras 3W Dataset 2.0.0

### 4.1 为什么选择 3W

3W Dataset 是 Petrobras 面向油井异常事件检测和分类公开的工业时序数据集，适合作为本项目核心数据来源。

项目中优先使用 3W 2.0.0。

主要特点：

- 多变量时间序列；
- 真实油井数据 + 模拟数据 + hand-drawn 数据；
- 真实工业背景；
- 适合异常检测、故障分类和提前预警；
- 数据格式适合按 instance 分块读取，不要求一次性放入内存；
- 适合作为边缘端“实时回放”的数据源。

### 4.2 数据规模概念

- 约 27 个过程变量；
- 约 2228 个时序 instance；
- 包含大量真实油井 instance；
- 数据集约 1.74 GB；
- 统一采用 Parquet 存储；
- 采样频率适合按实时流回放。

### 4.3 异常类别

3W 包含 Normal 和多类异常事件，例如：

- Abrupt Increase of BSW；
- Spurious Closure of DHSV；
- Severe Slugging；
- Flow Instability；
- Rapid Productivity Loss；
- Quick Restriction in PCK；
- Scaling in PCK；
- Hydrate in Production Line；
- Hydrate in Service Line。

### 4.4 第一版不要直接做 10 分类

原因：

- 各异常类别样本数极不均衡；
- 真实 / 模拟 / hand-drawn 数据域不同；
- 一开始做完整多分类容易被类别不平衡、缺失变量和域偏移拖慢。

推荐第一阶段只做：

```text
0 Normal
3 Severe Slugging
4 Flow Instability
9 Hydrate in Service Line
```

即：**4 分类**。

后续再逐步扩展到更多异常类型。

---

## 5. 第一版传感器变量选择

虽然 3W 2.0.0 有更多变量，但为了减少缺失值和跨数据源不一致问题，第一版只使用 7 个经典核心变量：

```text
P-PDG        Downhole Pressure
P-TPT        Subsea Tree Pressure
T-TPT        Subsea Tree Temperature
P-MON-CKP    Pressure Upstream of Production Choke
T-JUS-CKP    Temperature Downstream of Production Choke
P-JUS-CKGL   Pressure Downstream of Gas Lift Choke
QGL          Gas Lift Flow Rate
```

后续扩展实验：

```text
7-variable General Model
VS
27-variable Real-Data Model
```

这可以成为报告中的一个研究问题。

---

## 6. 总体系统架构

```text
┌─────────────────────────────────────────────────┐
│                Presentation Layer               │
│                                                 │
│  Vue 3 + TypeScript + ECharts                   │
│  Dashboard / Alarm / AI Copilot / Model Center │
└───────────────────────┬─────────────────────────┘
                        │ REST + WebSocket
                        ▼
┌─────────────────────────────────────────────────┐
│                   Cloud Layer                   │
│              Alibaba Cloud ECS 2C2G             │
│                                                 │
│  FastAPI                                        │
│  ├── Telemetry Service                          │
│  ├── Alarm Service                              │
│  ├── AI Inference Service                       │
│  ├── Diagnosis Service                          │
│  └── WebSocket Service                          │
│                                                 │
│  PostgreSQL + pgvector          Mosquitto MQTT  │
└───────────────────────┬─────────────────────────┘
                        │ MQTT
                        ▼
┌─────────────────────────────────────────────────┐
│                    Edge Layer                   │
│              Raspberry Pi 4B 2GB                │
│                                                 │
│  Edge Agent                                     │
│  ├── 3W Parquet Replay                          │
│  ├── Data Preprocessing                         │
│  ├── MQTT Publisher                             │
│  ├── Heartbeat                                  │
│  └── Optional Edge AI                           │
└─────────────────────────────────────────────────┘


               Offline Training Environment

┌─────────────────────────────────────────────────┐
│             MacBook Pro M1 Pro 16GB             │
│                                                 │
│  EDA / XGBoost / TCN / SHAP / RAG Indexing     │
│  PyTorch MPS                                    │
│                                                 │
│               ↓ model artifacts                 │
│          model.pt / model.json / metadata       │
└─────────────────────────────────────────────────┘
```

---

## 7. 设备角色分工

### 7.1 MacBook Pro

负责：

- 3W Dataset 下载与清洗；
- EDA；
- 训练 / 验证 / 测试集划分；
- 特征工程；
- Isolation Forest；
- XGBoost；
- PyTorch TCN；
- SHAP；
- RAG 文档解析、切分、Embedding、索引构建；
- 模型评估；
- 模型导出。

PyTorch 深度学习训练优先使用 MPS：

```python
device = "mps"
```

### 7.2 Raspberry Pi 4B

定位：**现场 Edge Gateway**。

第一阶段只负责：

- 读取 3W Parquet；
- 模拟实时采集；
- 传感器数据预处理；
- MQTT Publish；
- Heartbeat；
- 接收云端控制指令。

后续可扩展：

- XGBoost 轻量 Edge AI；
- 本地一级异常检测；
- 网络中断缓存与重传。

### 7.3 Alibaba Cloud ECS 2C2G

负责生产环境：

- Nginx；
- Vue3 静态文件；
- FastAPI；
- PostgreSQL；
- pgvector；
- Mosquitto MQTT Broker；
- WebSocket；
- 轻量模型推理；
- 报警逻辑；
- RAG orchestration；
- LLM API 调用。

不负责：

- 深度学习训练；
- 大规模 SHAP；
- 本地运行 7B+ LLM；
- LLM 微调。

### 7.4 LLM

使用云端 API。

LLM 不直接读取原始传感器并“猜故障”。

LLM 输入应来自：

- 模型预测结果；
- 置信度；
- SHAP 特征贡献；
- 关键变量趋势；
- RAG 检索到的行业资料。

LLM 负责：

- 生成面向人的异常解释；
- 生成辅助检查建议；
- 汇总历史趋势；
- 给出知识来源引用。

---

## 8. 端到端数据流

```text
3W Dataset
   │
   │ Parquet
   ▼
Raspberry Pi
Data Replay
   │
   │ MQTT
   ▼
Alibaba Cloud
FastAPI / MQTT Consumer
   │
   ├──────────────→ PostgreSQL
   │
   ▼
Sliding Window Buffer
   │
   ▼
AI Inference
   │
   ├── Normal
   │
   └── Abnormal
          │
          ▼
    Event Classification
          │
          ▼
      Alarm Engine
          │
          ├──────────→ WebSocket → Vue
          │
          ▼
    Explainability Layer
          │
          ▼
      RAG Retrieval
          │
          ▼
          LLM
          │
          ▼
   AI Diagnosis Report
```

---

## 9. AI 技术路线

### 9.1 Level 1：异常检测

目标：

```text
Normal / Abnormal
```

#### 模型 A：Isolation Forest

用途：

- 无监督异常检测 baseline；
- 只学习正常状态；
- 体现“没有充分故障标签时如何识别异常”。

#### 模型 B：XGBoost

用途：

- 工程 baseline；
- 二分类或多分类；
- 训练快、推理快；
- 可在 Mac、ECS、Pi 上运行；
- SHAP 解释方便。

推荐输入：窗口级统计特征。

假设窗口长度：

```text
180 s
```

每个变量提取：

```text
mean
std
min
max
median
range
slope
last value
first difference
```

约 7 个变量 × 8~9 个统计特征。

### 9.2 Level 2：异常事件分类

第一版：

```text
Normal
Severe Slugging
Flow Instability
Hydrate in Service Line
```

输出形式：

```text
Normal                    2.4%
Severe Slugging           4.7%
Flow Instability         91.2%
Hydrate in Service Line   1.7%
```

### 9.3 深度学习主模型：TCN

推荐使用 TCN，而不是一开始上大型 Transformer。

原因：

- 参数量小；
- 适合多变量时序；
- M1 Pro MPS 可训练；
- 推理开销低；
- 课程报告容易解释。

示意网络：

```text
Input: [B, C=7, T=180]
        │
        ▼
Conv1D 32, dilation=1
        │
        ▼
Conv1D 64, dilation=2
        │
        ▼
Conv1D 64, dilation=4
        │
        ▼
Global Pooling
        │
        ▼
FC
        │
        ▼
Softmax
```

参数量无需超过百万级。

### 9.4 模型组合

```text
Isolation Forest
    └── Unsupervised Baseline

XGBoost
    └── Traditional ML

TCN
    └── Deep Time-Series Learning
```

不建议堆叠过多模型：

- CNN + LSTM + Transformer + GAN + GNN + LLM 全部做；
- 课程项目以“完整工程 + 清晰实验”为优先。

---

## 10. 模型评估指标

至少包含：

```text
Accuracy
Precision
Recall
Macro F1
Confusion Matrix
Inference Latency
```

如果做提前预警，应增加：

```text
Detection Delay
Early Warning Lead Time
```

对于类别不平衡，优先看：

```text
Macro F1
Per-class Recall
Confusion Matrix
```

而不是只看 Accuracy。

---

## 11. 数据划分原则

### 11.1 禁止随机打散时间点

错误做法：

```text
12:00:01 → Train
12:00:02 → Test
12:00:03 → Train
```

会产生严重 Time-Series Data Leakage。

### 11.2 正确做法

按：

```text
instance
或
well_id
```

进行分组划分。

例如：

```text
Well A / B / C → Train
Well D / E     → Validation
Well F / G     → Test
```

可考虑：

```text
GroupKFold(group=well_id)
```

### 11.3 模拟 / 真实数据策略

推荐：

- 模拟数据可用于训练增强；
- 核心测试指标尽量优先报告真实油井数据；
- 可额外研究模拟数据 → 真实数据的泛化能力。

---

## 12. 可解释 AI

优先使用 SHAP。

目的：回答：

> 为什么模型认为这是 Flow Instability？

示例：

```text
Top Contributing Variables

P-TPT       +31.7%
P-PDG       +24.8%
QGL         +16.2%
T-TPT        +9.7%
```

同时展示：

```text
P-TPT
Normal baseline     8.14 MPa
Current             7.31 MPa
Deviation          -10.2%
Trend               ↓
```

XGBoost 可直接使用 SHAP TreeExplainer。

TCN 的解释可以作为后续扩展，例如 Captum / Integrated Gradients，不列为 P0。

---

## 13. RAG + LLM 辅助诊断

### 13.1 正确职责划分

不要：

```text
Sensor Data → LLM → 猜故障
```

应当：

```text
Sensor Data
    ↓
ML / DL
    ↓
Fault Probability
    +
SHAP / Trend Analysis
    +
Knowledge Retrieval
    ↓
LLM
    ↓
Human-readable Diagnosis
```

### 13.2 LLM 上下文模板

```text
Detected event:
Flow Instability

Confidence:
91.2%

Main abnormal variables:
P-TPT: -10.2%
P-PDG: +7.4%
QGL: oscillating

Model explanation:
P-TPT and QGL contributed most.

Retrieved documents:
[Document A ...]
[Document B ...]
```

### 13.3 LLM 输出格式

```text
诊断摘要
异常依据
可能原因
建议检查
知识依据
```

必须增加免责声明：

> AI 结果仅用于辅助分析与教学演示，不构成实际油井控制指令或生产操作依据。

### 13.4 RAG 知识库

可收集：

- 石油/油气生产安全规范；
- 流动保障相关公开资料；
- 水合物、段塞流、流动不稳定相关文档；
- 设备与操作公开资料；
- 事故案例；
- 课程提供资料。

第一版知识库规模无需太大。

推荐：

```text
PostgreSQL + pgvector
```

或者：

```text
FAISS + metadata in PostgreSQL
```

若 ECS 2GB 内存紧张，优先 FAISS 或轻量 pgvector。

---

## 14. Edge 端设计

### 14.1 Edge Agent 模块

```text
edge-agent/
├── replay.py
├── mqtt_client.py
├── preprocessing.py
├── heartbeat.py
├── config.py
└── main.py
```

### 14.2 主要职责

```text
读取 3W Parquet
      ↓
模拟实时采集
      ↓
构造 Telemetry
      ↓
MQTT Publish
```

### 14.3 Replay Speed

支持：

```text
1×
5×
10×
20×
```

答辩演示时可用 10× 或 20×。

### 14.4 Telemetry JSON 示例

```json
{
  "device_id": "edge-pi-01",
  "well_id": "WELL-00014",
  "timestamp": "2026-09-07T14:32:15",
  "sequence": 18241,
  "measurements": {
    "P_PDG": 19827340.2,
    "P_TPT": 8123910.4,
    "T_TPT": 63.12,
    "P_MON_CKP": 4293812.5,
    "T_JUS_CKP": 51.31,
    "P_JUS_CKGL": 5319021.2,
    "QGL": 0.0184
  }
}
```

---

## 15. MQTT 设计

### 15.1 Topic

```text
3w/edge/{device_id}/telemetry
3w/edge/{device_id}/status
3w/edge/{device_id}/command
3w/well/{well_id}/alarm
```

示例：

```text
3w/edge/pi-01/telemetry
3w/edge/pi-01/status
3w/edge/pi-01/command
```

### 15.2 云端控制指令

```text
START
STOP
PAUSE
SET_SPEED
LOAD_INSTANCE
```

典型链路：

```text
Web
 ↓
FastAPI
 ↓
MQTT
 ↓
Raspberry Pi
```

---

## 16. Cloud Backend 设计

### 16.1 推荐技术栈

```text
Python
FastAPI
SQLAlchemy
Pydantic
PostgreSQL
pgvector
Mosquitto
WebSocket
```

### 16.2 FastAPI 核心服务

```text
Telemetry Service
Alarm Service
AI Inference Service
Diagnosis Service
Knowledge Service
Model Service
Edge Device Service
WebSocket Service
```

### 16.3 推荐 API 分组

```text
/api/auth
/api/wells
/api/telemetry
/api/alarms
/api/inference
/api/diagnosis
/api/models
/api/edge-devices
/api/knowledge
/api/replay
```

---

## 17. 数据库设计

核心表建议：

```text
users
wells
edge_devices
telemetry
inference_results
alarms
diagnosis_reports
model_versions
```

RAG 扩展：

```text
documents
document_chunks
```

### 17.1 telemetry 表建议字段

```text
id
well_id
timestamp

p_pdg
p_tpt
t_tpt
p_mon_ckp
t_jus_ckp
p_jus_ckgl
qgl

extras JSONB
```

使用 `extras JSONB` 的原因：

- 未来扩展 27 个变量时不必重构表结构；
- 可存储暂未正式建列的新传感器。

### 17.2 inference_results

建议字段：

```text
id
well_id
model_version_id
timestamp
window_start
window_end
predicted_class
confidence
probabilities JSONB
anomaly_score
latency_ms
created_at
```

### 17.3 alarms

建议字段：

```text
id
well_id
inference_result_id
severity
event_type
status
message
raised_at
acknowledged_at
resolved_at
acknowledged_by
```

报警状态：

```text
UNACKNOWLEDGED
ACKNOWLEDGED
RESOLVED
```

---

## 18. Web 页面设计

第一版严格控制在 7 个核心页面。

### 18.1 Dashboard

展示：

```text
Wells
Online
Active Alarms
Critical Events
```

以及：

- 油井状态卡片；
- 报警趋势；
- 异常事件分布；
- 在线 Edge Device 数量。

### 18.2 油井实时监测

核心展示：

```text
WELL-00014

Status
● Abnormal

Risk
HIGH

AI Confidence
91.2%
```

实时 ECharts：

```text
P-PDG
P-TPT
T-TPT
QGL
...
```

以及：

```text
Current Prediction
Flow Instability
91.2%
```

### 18.3 报警中心

表格字段：

```text
Time
Well
Severity
Event
Confidence
Status
```

支持：

```text
Unacknowledged
Acknowledged
Resolved
```

### 18.4 AI 智能诊断

四个区域：

```text
Prediction
Feature Explanation
Sensor Trend
RAG Diagnosis
```

例如：

```text
AI Prediction
Flow Instability    91.2%

Top Evidence
P-TPT               31.7%
P-PDG               24.8%
QGL                 16.2%

AI Diagnosis
...
```

### 18.5 历史事件

支持按：

- 油井；
- 日期；
- 异常类别；

筛选。

支持展示一次异常从 Normal 到异常发生的完整时间过程。

### 18.6 Edge 设备 / 数据回放

展示：

```text
Edge Device
pi-01

Status
ONLINE

CPU
18%

Last Heartbeat
2 sec ago

Replay
WELL-00014_xxx.parquet

Speed
20×
```

支持：

```text
Start
Pause
Stop
Set Speed
Load Instance
```

### 18.7 模型中心

展示：

```text
Model Version
TCN-v1.3

Status
Active

Accuracy
92.8%

Macro F1
0.901

Latency
14 ms
```

支持：

- XGBoost / TCN 对比；
- Confusion Matrix；
- 模型版本切换（后期）；
- 当前 Active Model 标识。

### 18.8 P1 页面：知识库管理

后期增加：

- PDF 上传；
- 文档解析状态；
- Chunk 数量；
- Embedding 状态；
- 搜索测试；
- 删除；
- 查看来源。

---

## 19. Web 技术栈

```text
Vue 3
TypeScript
Pinia
Vue Router
ECharts
Element Plus
Axios
WebSocket
```

不建议第一版引入过多 UI 框架。

---

## 20. 部署方案

### 20.1 Docker Compose

ECS 上推荐：

```text
Docker Compose

├── nginx
├── api
├── postgres
└── mosquitto
```

可选：

```text
pgvector
```

### 20.2 第一版不要部署的组件

```text
Kafka
Redis
RabbitMQ
Elasticsearch
Milvus
Prometheus
Grafana
Kubernetes
```

理由：

- ECS 只有 2C2G；
- 本项目是本科课程工程原型；
- 复杂中间件会显著提高故障率和维护成本；
- 在报告中可以写为“生产级横向扩展方向”，但无需实际部署。

### 20.3 Nginx

负责：

- Vue 静态资源；
- `/api` 反向代理 FastAPI；
- `/ws` WebSocket；
- TLS；
- 基本请求限制。

---

## 21. Git Monorepo 建议

```text
oilwell-ai/
│
├── apps/
│   ├── web/                 # Vue3
│   └── api/                 # FastAPI
│
├── services/
│   └── edge-agent/          # Raspberry Pi
│
├── ml/
│   ├── notebooks/
│   ├── data/
│   ├── preprocessing/
│   ├── features/
│   ├── datasets/
│   ├── models/
│   ├── training/
│   ├── evaluation/
│   └── artifacts/
│
├── rag/
│   ├── documents/
│   ├── ingestion/
│   ├── retrieval/
│   └── prompts/
│
├── infra/
│   ├── docker/
│   ├── nginx/
│   ├── mosquitto/
│   └── docker-compose.yml
│
├── docs/
│   ├── architecture/
│   ├── database/
│   ├── api/
│   ├── experiments/
│   └── presentation/
│
├── scripts/
│   ├── download_3w.py
│   ├── init_db.py
│   └── deploy.sh
│
├── tests/
│
├── .github/
│   └── workflows/
│
├── README.md
├── LICENSE
└── .gitignore
```

### 21.1 不要把完整 3W 数据提交到 Git

仓库中只保留：

```text
scripts/download_3w.py
数据版本说明
数据来源
citation
sample data
```

模型 artifact 若较大可使用 Git LFS，或者在 Release 中提供。

---

## 22. 生产模型与模型制品

推荐输出：

```text
xgboost_model.json
xgboost_metadata.json

tcn_model.pt
tcn_config.json
tcn_metadata.json

scaler.pkl
feature_schema.json
class_mapping.json
```

所有模型必须记录：

```text
version
training data version
features
window size
class mapping
metrics
created_at
git commit hash
```

---

## 23. 第一阶段窗口设计建议

初始实验建议：

```text
window_size = 180 seconds
stride = 10~30 seconds
channels = 7
```

不要把全部滑动窗口一次性 materialize 到 RAM。

推荐：

- 按 instance 读取；
- 使用 PyTorch Dataset / DataLoader 动态生成窗口；
- 必要时使用 Parquet / memmap；
- float32；
- 控制 batch size。

M1 Pro 16GB 足以应对当前规划。

---

## 24. 硬件与算力策略

### 24.1 本机可完成

- EDA；
- 数据清洗；
- Isolation Forest；
- XGBoost；
- TCN；
- SHAP；
- RAG indexing；
- 全栈开发。

### 24.2 暂不租云 GPU

只有出现以下情况再考虑：

- 大规模超参数搜索；
- 大型 Transformer 时序模型；
- 多轮重型深度学习实验；
- LLM LoRA / QLoRA 微调。

### 24.3 生产服务器只负责推理

```text
Training Environment
Mac / Optional GPU
       ↓
model artifacts
       ↓
Production ECS CPU
```

---

## 25. 项目优先级

### P0：必须完成

- 3W 数据下载与分析；
- 数据清洗；
- 7 个核心变量；
- Train / Val / Test 分组划分；
- Vue3 前端；
- FastAPI 后端；
- PostgreSQL；
- Raspberry Pi 数据回放；
- MQTT；
- 实时传感器曲线；
- XGBoost；
- TCN；
- 实时推理；
- 报警系统；
- Docker Compose 部署；
- README；
- 基本测试。

达到 P0 即可形成高质量完整项目。

### P1：强烈建议完成

- SHAP；
- RAG；
- LLM 诊断报告；
- 模型中心；
- 历史事件回放；
- 文档来源引用；
- 模型版本管理。

### P2：有时间再做

- 10 类异常完整分类；
- Edge AI；
- 27 变量真实数据模型；
- Early Warning 专门模型；
- Captum / Integrated Gradients；
- Agent；
- CI/CD；
- 网络断连缓存；
- 更复杂的权限系统。

---

## 26. 建议时间规划

### 第 2~5 周：MVP

完成：

```text
3W Dataset
+
数据读取
+
数据库
+
FastAPI
+
Vue3
+
时序曲线
+
历史 / 实时回放
+
MQTT
```

目标：即使 AI 未完成，也有完整可运行信息系统。

### 第 6~9 周：核心 AI

完成：

```text
EDA
↓
异常检测 Baseline
↓
XGBoost
↓
TCN
↓
模型评估
↓
Model API
```

### 第 10~12 周：智能诊断

加入：

```text
SHAP
+
Knowledge Base
+
RAG
+
LLM Diagnosis
```

### 第 13~14 周：工程化

加入：

```text
Docker Compose
WebSocket
Alarm Workflow
Edge Device Management
日志
基础权限
```

### 第 15 周以后：交付

只做：

```text
测试
Bug Fix
实验结果整理
README
架构图
课程报告
PPT
答辩 Demo 脚本
```

不要在最后两周增加重大新模型。

---

## 27. 答辩 Demo 设计

推荐现场流程：

```text
1. 打开 Dashboard
2. 展示 Edge Device 在线
3. 选择 WELL-XXXX
4. 通过网页给树莓派发送 LOAD_INSTANCE
5. 设置 Replay Speed = 20×
6. 点击 Start
7. 实时曲线开始变化
8. AI 持续输出 Normal
9. 异常前兆出现
10. 系统产生 Warning / High Risk
11. AI 分类：Flow Instability 91.2%
12. 打开 SHAP：展示关键变量
13. 打开 AI Diagnosis：展示 RAG + LLM 解释
14. 查看 Alarm Center
15. Acknowledge Alarm
16. 打开 Model Center 对比 XGBoost / TCN
```

这一流程可以完整体现：

```text
Edge
→ MQTT
→ Cloud
→ Database
→ AI
→ Alarm
→ XAI
→ RAG
→ LLM
→ Web
```

---

## 28. 课程报告建议章节

```text
1. 绪论
2. 油井异常监测业务与需求分析
3. 3W Dataset 与数据分析
4. 系统总体架构设计
5. 边云协同数据采集设计
6. 多变量时序异常检测与分类方法
7. 可解释 AI 与辅助诊断设计
8. RAG 知识服务设计
9. 数据库与后端设计
10. 前端与可视化设计
11. 系统实现与部署
12. 模型实验与结果分析
13. 系统测试
14. 总结与展望
```

---

## 29. AI 实验建议

### Experiment 1

```text
Isolation Forest
Normal vs Abnormal
```

### Experiment 2

```text
XGBoost
4-class classification
```

### Experiment 3

```text
TCN
4-class classification
```

### Experiment 4

```text
XGBoost vs TCN
Accuracy / Macro F1 / Latency
```

### Experiment 5

```text
Real-only test
模拟训练增强是否提升真实数据泛化
```

### Experiment 6（可选）

```text
7 variables vs 27 variables
```

### Experiment 7（可选）

```text
不同 window_size
60s / 120s / 180s / 300s
```

---

## 30. 工程原则

### 30.1 首要目标

```text
可运行
> 可复现
> 可部署
> 可演示
> 可解释
> 再追求模型指标
```

### 30.2 不要为技术炫技牺牲完整度

禁止式思路：

```text
一开始就：
Transformer + Agent + 10-class + Digital Twin + Kubernetes
```

优先：

```text
MVP
↓
AI
↓
XAI
↓
RAG
↓
工程化
```

### 30.3 AI 不直接控制生产

系统定位必须始终是：

```text
Monitoring
Detection
Diagnosis
Decision Support
```

不是：

```text
Automatic Production Control
```

---

## 31. 编码与项目约定建议

### Python

- Python 3.11+；
- Ruff；
- Black（可选，如与 Ruff Formatter 重复则二选一）；
- Pytest；
- Pydantic v2；
- 类型标注；
- `.env` 配置；
- 不把 secret 提交到 Git。

### Frontend

- Vue 3 Composition API；
- TypeScript strict；
- Pinia；
- ESLint；
- Prettier；
- API Client 统一封装；
- WebSocket Client 统一管理。

### Git

推荐分支：

```text
main
feature/*
fix/*
```

Commit Message 可使用：

```text
feat:
fix:
refactor:
docs:
test:
chore:
```

---

## 32. Codex 启动项目时的首批任务

建议 Codex 不要一次生成整个项目，而按以下顺序实现。

### Phase 0：Scaffold

1. 创建 monorepo 目录；
2. 创建 FastAPI skeleton；
3. 创建 Vue3 + TypeScript skeleton；
4. 创建 Docker Compose；
5. 创建 PostgreSQL / Mosquitto 配置；
6. 创建 `.env.example`；
7. 创建基础 README；
8. 创建 Makefile 或 Taskfile。

### Phase 1：Data & Edge

1. 编写 3W dataset downloader；
2. 实现 dataset metadata parser；
3. 实现 selected 7 sensors schema；
4. 实现 Raspberry Pi replay service；
5. MQTT telemetry publish；
6. cloud MQTT consumer；
7. telemetry 入库；
8. WebSocket 推送。

### Phase 2：Frontend MVP

1. Dashboard；
2. Well real-time monitor；
3. Edge device page；
4. Alarm center；
5. 历史 telemetry 查询。

### Phase 3：ML Baseline

1. instance / well 分组 split；
2. feature extractor；
3. Isolation Forest；
4. XGBoost；
5. evaluation pipeline；
6. model registry metadata；
7. inference service。

### Phase 4：TCN

1. dynamic sliding-window Dataset；
2. DataLoader；
3. PyTorch MPS device support；
4. TCN model；
5. train script；
6. checkpoint；
7. evaluation；
8. serving wrapper。

### Phase 5：XAI

1. SHAP for XGBoost；
2. top feature contributions API；
3. AI Diagnosis page visualization。

### Phase 6：RAG

1. document ingestion；
2. chunking；
3. embedding；
4. pgvector / FAISS index；
5. retrieval API；
6. diagnosis prompt；
7. LLM API adapter；
8. citation output。

### Phase 7：Production Hardening

1. Nginx；
2. Docker Compose production profile；
3. health checks；
4. structured logs；
5. test suite；
6. seed data；
7. deployment docs；
8. demo script。

---

## 33. 首次 EDA 必须输出的内容

在正式确定模型前，先完成并保存以下统计结果：

```text
1. 每个 class 的 instance 数量
2. Real / Simulated / Hand-drawn 数量
3. 每个 instance 持续时间
4. 每个传感器缺失率
5. 7 个核心变量覆盖率
6. 每类异常的持续时间分布
7. 不同 well 的数据量
8. 不同 class 在不同 well 中的分布
9. 传感器数值范围
10. outlier / frozen variable 情况
11. transient label 使用情况
```

EDA 输出建议保存：

```text
ml/reports/eda_summary.json
ml/reports/eda_summary.md
ml/reports/figures/
```

---

## 34. 第一版模型设计的默认参数建议

可作为起点，不视为最终结论：

```text
Selected Sensors: 7
Window Size: 180 s
Stride: 30 s
Batch Size: 64
Float Type: float32
```

XGBoost：

```text
max_depth: 6
learning_rate: 0.05~0.1
n_estimators: 300~800
subsample: 0.8
colsample_bytree: 0.8
```

TCN：

```text
channels: [32, 64, 64]
kernel_size: 3
dilations: [1, 2, 4]
dropout: 0.1~0.2
optimizer: AdamW
```

具体参数由实验决定。

---

## 35. 报警逻辑建议

不要单次预测异常就立刻产生 Critical Alarm。

推荐引入连续窗口逻辑：

```text
P(abnormal) > 0.70
连续 2~3 个窗口
→ Warning

P(abnormal) > 0.85
连续 2~3 个窗口
→ High

P(abnormal) > 0.95
且故障类别稳定
→ Critical
```

具体阈值后续通过验证集校准。

目的：

- 减少抖动；
- 贴近工业报警系统；
- 展示“信息系统工程”而非单纯模型输出。

---

## 36. 实时推理设计

云端维护每口井的 Ring Buffer：

```text
well_id → latest N seconds telemetry
```

每收到新数据：

```text
append
↓
if enough samples:
    preprocess
    ↓
    inference
    ↓
    alarm state machine
    ↓
    persist result
    ↓
    WebSocket push
```

避免每个点都从数据库重新查询完整窗口。

---

## 37. Demo 模式与生产模式

建议配置两个模式：

### Demo Mode

```text
Replay Speed: 10× / 20×
Reduced inference stride
Known anomaly instance
Fast alert trigger
```

### Normal Mode

```text
Replay Speed: 1×
Normal sampling semantics
Production-like thresholds
```

通过环境变量或配置切换。

---

## 38. 项目风险与规避

### 风险 1：类别不平衡

应对：

- 先做 4 分类；
- class weighting；
- Macro F1；
- 合理采样；
- 分析真实 / 模拟域。

### 风险 2：Missing Variables

应对：

- 第一版固定 7 个核心变量；
- 27 变量作为扩展实验。

### 风险 3：内存不足

应对：

- 按 instance 加载；
- DataLoader 动态窗口；
- float32；
- 不一次性展开全部窗口。

### 风险 4：2C2G ECS 资源不足

应对：

- 不部署本地 LLM；
- 不上重型中间件；
- 只部署推理模型；
- RAG 使用轻量索引。

### 风险 5：RAG 成为主线拖慢项目

应对：

- RAG 属于 P1；
- P0 先确保工业时序 AI 完整闭环。

### 风险 6：模型很好但系统没做完

应对：

- MVP 优先；
- 先系统，再高级模型；
- 第 13 周后冻结重大功能。

---

## 39. 最终项目应体现的行业趋势

项目需要自然体现，而不是堆概念：

```text
Industrial IoT
Edge-Cloud Collaboration
Real-time Monitoring
Predictive / Diagnostic AI
Multivariate Time-Series Learning
Explainable AI
RAG
Generative AI Copilot
Cloud-native Deployment
Model Lifecycle Awareness
```

其中最重要的是：

> AI 不是孤立模型，而是嵌入数据采集、实时监控、报警、诊断和知识服务的完整业务流程中。

---

## 40. 最终验收标准

项目达到以下条件即可视为完成：

### 系统

- [ ] Raspberry Pi 可以读取 3W instance 并 MQTT 回放；
- [ ] ECS 可以接收并入库；
- [ ] Vue 可以实时显示；
- [ ] WebSocket 可实时推送；
- [ ] 可以产生报警；
- [ ] 报警可确认与解决；
- [ ] 可以查询历史事件。

### AI

- [ ] Isolation Forest baseline；
- [ ] XGBoost baseline；
- [ ] TCN；
- [ ] 4 类异常识别；
- [ ] 完整测试集指标；
- [ ] Confusion Matrix；
- [ ] Inference Latency；
- [ ] SHAP（P1）。

### RAG / LLM

- [ ] 知识库文档；
- [ ] 检索；
- [ ] LLM 诊断；
- [ ] 引用来源；
- [ ] 辅助诊断免责声明。

### 工程

- [ ] Docker Compose；
- [ ] `.env.example`；
- [ ] README；
- [ ] 架构图；
- [ ] 数据库说明；
- [ ] API 文档；
- [ ] 模型实验记录；
- [ ] 部署文档；
- [ ] Git 历史清晰；
- [ ] Demo 流程可复现。

---

## 41. Codex 的核心约束

Codex 在后续实现时应遵守以下约束：

1. 优先保持项目可运行，不要一次实现全部高级功能；
2. 不要把完整 3W 数据提交进 Git；
3. 不要把任何 API Key / Password 提交进 Git；
4. 后端优先 FastAPI，不改回 Flask；
5. 前端采用 Vue3 + TypeScript；
6. 数据库采用 PostgreSQL；
7. MQTT 使用 Mosquitto；
8. AI 主线为 XGBoost + TCN；
9. 第一版使用 7 个核心传感器；
10. 第一版只保证 4 分类；
11. 模型训练在 Mac 完成，生产 ECS 只做推理；
12. LLM 使用外部 API，不在 2C2G ECS 本地部署大模型；
13. 所有模型结果应可追溯到 model version；
14. 时间序列 train/test split 必须按 instance 或 well 分组；
15. 系统必须保留清晰的 P0 / P1 / P2 边界；
16. 第 13 周以后不引入破坏性大改；
17. 所有对生产安全相关建议必须标注“辅助分析，不构成实际操作指令”。

---

## 42. 推荐下一步

Codex 启动后，第一阶段不要立即写 TCN。

优先顺序：

```text
Repository Scaffold
↓
3W Download Script
↓
Dataset Inspector / EDA
↓
Database Schema
↓
MQTT Replay
↓
FastAPI Consumer
↓
Vue Real-time Monitor
↓
XGBoost Baseline
↓
TCN
↓
SHAP
↓
RAG / LLM
```

第一周开发目标应当是：

> 从 3W 数据集中选一个 instance，由 Mac 或 Raspberry Pi 模拟实时发送，经 MQTT 到 FastAPI，写入 PostgreSQL，并在 Vue 页面实时画出至少 4 条传感器曲线。

一旦这条链路跑通，整个项目的工程主干就成立了。

