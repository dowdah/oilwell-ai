# Phase B 可读数据协议

## 固定任务

- Normal = `0`; Abnormal = 当前可读 selection 中的 `3` / `4` / `9`。
- 特征：7 variables、180 秒窗口、10 秒步长、63 statistical features。
- 划分单位：井；不随机切窗口。
- 阈值和候选只使用 validation；test 井仅在最终候选固定后评估一次。

## 数据与可复现性

- source dataset root: `/Users/sheldon/Documents/codex-projects/oilwell-ai/ml/data/raw/petrobras-3w/dataset`
- selection SHA-256: `b18806287d5c1dad5c4e3b2572b9645b94c209b47a049b1cbf522786361c1545`
- split SHA-256: `d114ac3b0763ee53ad06fb970fa35acaf52b161a700c537ed030740b116c69d6`
- 可用实例：55；排除：132。完整排除清单、文件哈希、连续时长与全零变量见 `../available-data-audit.json`。

## 冻结井级划分

| 集合 | 井 | 实例 | Normal 窗口 | Abnormal 窗口 | 原始类实例 |
| --- | --- | ---: | ---: | ---: | --- |
| train | WELL-00001, WELL-00006, WELL-00015, WELL-00016, WELL-00037, WELL-00038 | 33 | 32405 | 12041 | 0:18, 3:1, 4:12, 9:2 |
| validation | WELL-00007, WELL-00020 | 5 | 1749 | 702 | 0:3, 4:1, 9:1 |
| test | WELL-00014 | 17 | 4923 | 23174 | 0:3, 3:8, 4:3, 9:3 |

## 覆盖边界

- 三个集合均同时具有 Normal 与 Abnormal 窗口，且井集合互斥。
- 原始异常事件类别的跨井覆盖由上表披露；未在 held-out test 出现的类别不得声称具有跨井泛化能力。
- 旧 C2 的 187 实例协议保存在 `../historical/c2-unreproduced-freeze/`，是历史记录，不是本实验输入。
