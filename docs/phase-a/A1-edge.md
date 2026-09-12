# A1 Edge replay

基准：`3e99c99179b0f6ccdabb20066e33e5adedc11cc0`。分支：`codex/phase-a-verification`。运行编号：`phase-a-20260913`（北京时间 2026-09-13；UTC 记录落在 2026-09-12）。本次只提交验证文档，未修改功能代码。

原始证据位于本工作树忽略目录 `docs/.local/phase-a/run-20260913/`，不包含在 Git 提交中。下面的“通过”均限定测试场景；本地固定样例、真实数据回放、旧部署结果分开记录。

## 结论

本地通过；旧部署失败。

## 验证与边界

- C1 `services/edge-agent/tests/test_replay.py`：11 passed，0.29 秒。覆盖命令拒绝、线程代际、持久化序列号跨重启/时钟倒退、无效时间戳/变量拒绝。
- 本地 C1 真实回放 241 点，逐点与源文件七变量和实际时间一致；START/PAUSE/STOP/SET_SPEED/LOAD_INSTANCE 回执对应 command_id，运行时 LOAD 被拒绝，暂停/停止后计数稳定。
- STOP/START 后 sequence 增大；进程重建与持久化检查来自单元测试，不冒充本次实际进程重启演练。
- Pi 源文件哈希与本地一致。但已部署 `_replay` 固定使用 `settings.well_id=WELL-00014`，与选中 WELL-00001 文件不符；初始化仍为 `int(time.time())`，没有 C1 的持久化租约。
- 实机尝试 1×，采集器等待 310 秒后超时；尝试范围 `1789215247–1789215557` 与旧记录重叠，未取得 240 个新样本的通过证据。
- 用户另行批准保留选中实例；最后已恢复 ONLINE、20×，无重启或序列号重置。

证据：`a1-unit.log`、`local-chain.json`、`deployed-findings.json`、`deployed-after.json`。

## 修改与回滚

未修改本阶段功能代码。只提交本文；撤销文档提交不影响服务。原工作区和 C2 未改动。
