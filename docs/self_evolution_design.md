# Self-Evolution System Design

> **对比**: Nexus Agent vs OpenClaw 自我进化能力
> **状态**: 设计中

---

## 1. OpenClaw 架构深度解析

经过对 OpenClaw 源码 (`src/agents/system-prompt.ts`, `src/config/includes.ts`) 的研究，发现其核心机制如下：

### 1.1 Context Injection (上下文注入)
OpenClaw 并非魔法，而是显式地将文件内容注入 System Prompt：
- **`system-prompt.ts`**: 检查 `contextFiles` 数组。
- **`soul.md` 检测**: 如果存在 `soul.md`，添加指令 *"If SOUL.md is present, embody its persona and tone..."*。
- **通用注入**: 所有 Context Files 被添加到 `# Project Context` 章节。
- **Runtime Info**: 动态构建 `Runtime` 字符串 (包含 OS, Node版本, Model, Capabilities)。

### 1.2 Config `$include` (模块化配置)
强大的配置加载机制 (`config/includes.ts`)：
- 支持 `"$include": "./path/to/file"` 或数组。
- 允许递归引用，实现配置的模块化复用。

### 1.3 Self-Update (自我更新)
CLI (`cli/update-cli.ts`) 封装了标准流程：
1. **Check**: 检查 Git 远程分支或 NPM 版本。
2. **Update**: 执行 `git pull --rebase` 或 `npm install -g`。
3. **Doctor**: 更新后运行自检脚本修复环境。

---

## 2. Nexus 当前状态 (Gap Analysis)

### ✅ 已有的相似概念

| OpenClaw | Nexus 等效 | 位置 |
|----------|------------|------|
| `soul.md` | System Prompt | `agent.py` |
| `skill.md` | Skill Cards | `skills/*.md` |
| `user.md` | User model (`language`, `policy`) | `models/user.py` |

### ❌ 缺失的关键能力

| 能力 | 问题 | 影响 |
|------|------|------|
| **User Context Injection** | User 偏好未注入 System Prompt | LLM 不知道用户语言/习惯 |
| **Menu Auto-Sync** | 菜单只在启动时设置，用户改偏好后不更新 | 用户体验断裂 |
| **Skill Marketplace** | 技能只能手动添加 | 无法自动下载新能力 |
| **Self-Update** | 无 `/update` 命令 | 无法一键升级 |

---

## 3. 当前 Menu 问题分析

```python
# telegram.py line 478-490 (启动时)
await application.bot.set_my_commands(cmds_en, language_code="en")
await application.bot.set_my_commands(cmds_zh, language_code="zh")

# telegram.py line 210 (per-chat)
await _telegram_app.bot.set_my_commands(commands=cmds, scope=BotCommandScopeChat(chat_id=chat_id))
```

**问题**：
1. 启动时只设置 `language_code="en/zh"` (Telegram 按用户 Telegram 语言选择，而非 Nexus 用户偏好)
2. `update_telegram_menu()` 函数存在，但只在特定操作后调用，**未在用户改变 language 偏好后自动触发**

---

## 4. Nexus 实施方案 (Refined)

### 4.1 System Prompt 动态构建器 (仿 OpenClaw)

**代码位置**: `app/core/prompt_builder.py` (新增)

```python
def build_system_prompt(user: User, agent_config: dict) -> str:
    # 1. Base Persona (Soul)
    soul_content = load_soul_file() or DEFAULT_SOUL
    
    # 2. User Context (User.md equivalent)
    user_context = f"""
    ## User Context
    - ID: {user.username}
    - Language: {user.language}
    - Role: {user.role}
    - Preferences: {json.dumps(user.policy)}
    """
    
    # 3. Dynamic Runtime Info
    runtime_info = get_runtime_status() # OS, Tools, Time
    
    # 4. Assemble
    return f"{soul_content}\n\n{user_context}\n\n{runtime_info}\n\n{SKILL_INSTRUCTIONS}"
```

### 4.2 配置热重载与 `$include` 支持

虽然不完全重写 Config Loader，但可以引入类似机制：
- 在 `agent.yaml` 或数据库配置中支持 `include: "path/to/segment.md"`
- 每次 Agent 初始化时重新加载，实现"热更"。

### 4.3 自我更新流程 (`/update` 指令)

模仿 OpenClaw `update-cli.ts`：

1. **User Command**: `/update` (Admin only)
2. **Nexus Action**:
   - `git fetch origin main`
   - Check raw commit hash
   - If new:
     - `git pull`
     - `docker-compose build nexus-app` (Optional, or just restart container)
     - `supervisorctl restart nexus-agent`
3. **Feedback**: 实时推送更新进度日志到 Chat。

---

## 5. 实施优先级

| 改进 | 复杂度 | 价值 | 优先级 |
|------|--------|------|--------|
| User Context Injection | 低 | 高 | 🔴 P1 |
| `/lang` 命令 + Menu Sync | 低 | 中 | 🟡 P2 |
| Skill Registry (Phase 1) | 中 | 中 | 🟢 P3 |
| NexusHub (Phase 2) | 高 | 高 | 📅 Future |

---

## 6. 与当前问题的关系

用户提到的 "menu 没有自动设置" 问题：
1. **根本原因**: Telegram 菜单是按 `language_code` 设置的，这是 Telegram 用户的界面语言，不是 Nexus 用户的偏好
2. **解决方案**: 实现 per-chat 菜单同步 (基于 Nexus User.language)

---

*待用户确认优先级后开始实施*
