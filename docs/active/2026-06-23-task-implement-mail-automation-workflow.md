# 任务: Implement mail automation workflow

## 基本信息
- 创建时间: 2026-06-23
- 负责人: ugreen
- 优先级: 高

## 任务描述
在 ~/hors/mailautomation 中实现本地邮件自动化流程，完成 IMAP 增量抓取、Codex 摘要、Obsidian 同日单文档更新、通知和定时/手动触发接入。

## 相关文档
- 计划文档: [../plans/2026-06-23-mail-automation-workflow.md](../plans/2026-06-23-mail-automation-workflow.md)

## 实施计划
1. 搭建工作目录、配置和状态文件布局
2. 实现 IMAP 增量抓取与 Keychain 凭据读取
3. 接入 Codex 摘要、Obsidian 更新和通知
4. 接入定时执行与快捷指令手动补跑
5. 验证并补齐运维文档

## 验收标准
- 能从 Keychain 读取凭据并成功连接 IMAP
- 同一天始终只更新一篇 Obsidian 笔记
- 每次执行都输出运行结果
- 支持每天 09:30 自动执行和手动补跑

## 进展记录
- 2026-06-23: 创建任务 - 待开始
- 2026-06-23: 在隔离 worktree `feature/mail-automation-impl` 中完成首版实现，已覆盖 IMAP collector、Codex 摘要交接、Obsidian 笔记更新、通知、主流程 orchestration、调度脚本与运维文档。
- 2026-06-23: 当前自动化测试 17 项通过；已验证 `collector.py --dry-run`、`run_summary.py --preview`、`note_writer.py --sample`、`main.py --dry-run`、`launchd` plist lint。
