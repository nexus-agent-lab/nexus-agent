---
name: cron_scheduler
description: 管理用户的定时任务，支持自然语言解析时间并转换为 Cron 表达式。
domain: scheduler
intent_keywords:
  - schedule
  - cron
  - reminder
  - every
  - daily
  - weekly
  - 定时
  - 提醒
  - 每天
  - 每周
---

# Cron Scheduler ⏱️

你拥有管理定时任务的能力。你可以为用户创建、列出和删除定时任务。

## 重要规则

1. **Cron 转换**: 如果用户使用自然语言（如 "每天早上9点"），你必须将其转换为标准的 Cron 表达式：
   - "每天早上9点" -> `0 9 * * *`
   - "每周一下午3点" -> `0 15 * * 1`
   - "每隔2小时" -> `0 */2 * * *`
   - "每月1号凌晨" -> `0 0 1 * *`

2. **描述清晰**: 在创建任务时，`description` 应该简洁明了，让用户一眼看出任务目的。

3. **权限隔离**: 工具会自动处理用户隔离，你只需要调用工具即可。

## Few-Shot 示例

### 示例 1: 创建日常提醒
**User**: 每天早上8:30提醒我检查邮件。
**Agent**: 好的，我为您设置了一个每天 8:30 的提醒。
**Action**: `schedule_cron_task(cron_expr="30 8 * * *", prompt="检查我的未读邮件并给出摘要", description="每日邮件提醒")`

### 示例 2: 定期自动化
**User**: 每周五下午5点帮我汇总本周的工作周报。
**Action**: `schedule_cron_task(cron_expr="0 17 * * 5", prompt="总结本周的所有任务执行情况和 Sandbox 中的分析结果，生成一份周报", description="周五工作汇总")`

### 示例 3: 查看任务
**User**: 我都设置了哪些定时任务？
**Action**: `list_scheduled_tasks()`

### 示例 4: 删除任务
**User**: 取消那个 8:30 的提醒。
**Agent**: (先调用 list_scheduled_tasks 找到 ID 为 5)
**Action**: `remove_scheduled_task(task_id=5)`

## 最佳实践
- 如果用户的时间描述模糊（如 "晚点提醒我"），请先询问具体时间。
- 在成功设置任务后，向用户确认具体的执行频率和内容。
