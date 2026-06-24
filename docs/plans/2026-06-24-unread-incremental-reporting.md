# 未读数与新增数双轨汇报 实施计划

> **Execution note:** After this plan is approved, use `horspowers:executing-plans` or `horspowers:subagent-driven-development` to implement it task-by-task in the current host.

**日期**: 2026-06-24

## 目标

在现有邮件自动化流程中，同时汇报“当前未读邮件数”和“自上次检查以来的新增邮件数”，并继续只对新增邮件生成摘要。

## 架构方案

保持现有增量抓取与摘要链路不变，在 collector 侧额外查询 IMAP `UNSEEN` 集合并向下游传递 `unread_count`。主流程、通知、命令行输出和 Obsidian 笔记统一消费这两个指标，其中 Obsidian 每次运行都追加 run 记录，即使本次没有新增邮件。

## 技术栈

- Python 3 标准库 (`imaplib`, `json`, `pathlib`, `datetime`)
- 现有 workflow 模块：`collector.py`, `main.py`, `note_writer.py`, `notifier.py`
- `pytest`

---

### Task 1: 用失败测试锁定双指标采集与暴露

**Files:**
- Modify: `/Users/ugreen/hors/mailautomation/tests/test_collector_runtime.py`
- Modify: `/Users/ugreen/hors/mailautomation/tests/test_orchestration.py`
- Modify: `/Users/ugreen/hors/mailautomation/tests/test_note_writer.py`
- Modify: `/Users/ugreen/hors/mailautomation/tests/test_notifier.py`

**Step 1: 为 collector 增加未读数测试**

写测试断言 `collect_incremental_mail()` 返回 `unread_count`，且 dry-run / fake fetch 场景不会破坏现有 `new_messages` 语义。

**Step 2: 为 orchestration 增加双指标 report 与 no-new-mail 行为测试**

写测试覆盖：
- report / CLI 结果包含 `unread_count`
- `unread_count > 0 && new_message_count == 0` 时仍会写 note、仍会通知、仍会返回 success
- 通知文案带 `未读 X / 新增 Y`

**Step 3: 为 note writer 锁定每次 run 都写指标**

写测试断言：
- run 记录顶部先写 `当前未读` 和 `本次新增`
- 无新增时仍追加 run，且正文为“无新增邮件”占位信息

**Step 4: 跑定向测试确认 RED**

Run: `.venv/bin/python -m pytest tests/test_collector_runtime.py tests/test_orchestration.py tests/test_note_writer.py tests/test_notifier.py -q`
Expected: 新增断言失败，证明行为尚未实现。

### Task 2: 最小实现 collector / workflow / note / notifier

**Files:**
- Modify: `/Users/ugreen/hors/mailautomation/src/collector.py`
- Modify: `/Users/ugreen/hors/mailautomation/src/main.py`
- Modify: `/Users/ugreen/hors/mailautomation/src/note_writer.py`
- Modify: `/Users/ugreen/hors/mailautomation/src/notifier.py`

**Step 1: collector 返回未读数**

在 IMAP 层查询 `UNSEEN` UID 集合，返回 `unread_count` 和 `unread_uids`，但摘要输入仍只使用增量 `new_messages`。

**Step 2: workflow report/CLI 贯穿双指标**

让 `run_workflow()` 在 success/no-new-mail 两条路径都写出 `unread_count`，并调整通知文案格式。

**Step 3: note writer 支持无新增也写 run**

更新日记写入逻辑，使每次 run 都追加记录，并在顶部/本次 run 中先展示两个指标。

**Step 4: 保持最小改动并跑定向测试转绿**

Run: `.venv/bin/python -m pytest tests/test_collector_runtime.py tests/test_orchestration.py tests/test_note_writer.py tests/test_notifier.py -q`
Expected: PASS

### Task 3: 做全量验证与真实运行验证

**Files:**
- Verify only

**Step 1: 跑全量测试**

Run: `.venv/bin/python -m pytest tests -q`
Expected: 全部通过。

**Step 2: 实际运行一次 workflow**

Run: `.venv/bin/python src/main.py`
Expected: 命令行 JSON 包含 `unread_count` 和 `new_message_count`，并成功执行。

**Step 3: 检查 Obsidian 与通知/日志结果**

验证：
- 当日日记 run 区块先展示两个指标
- 通知文案带 `未读 X / 新增 Y`
- state 中 `last_run_summary` 含 `unread_count`

**Step 4: 如需要，再验证 launchd 手动触发一次**

Run: `launchctl kickstart -k gui/501/com.ugreen.mailautomation`
Expected: 走同样逻辑，不回退到旧行为。
