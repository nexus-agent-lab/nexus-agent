# Phase 30: Hierarchical Context + Event Triggers (Discussion Draft)

## Part A: OpenViking 模式在各子系统的适用性

> 核心思想：不引入 OpenViking 包，只借鉴 3 个设计模式：**L0 摘要层**、**分组检索**、**Score Propagation**

### 1. Memory System（记忆系统）
| 当前状态 | 改进方案 |
|---------|---------|
| 全文存储，全文 Embedding | 新增 `abstract` 字段 (L0)，基于摘要做 Embedding |
| 扁平检索（一次 cosine search） | 按 `category` 分组，两步检索 |
| 全部加载到 Prompt | L0 筛选 → L1 概览 → 按需加载全文 |

**改动量**: `Memory` 模型 +1 字段，`memory.py` 修改检索逻辑 (~50 行)

---

### 2. Skill System（技能加载）⭐ 最大收益
| 当前状态 | 改进方案 |
|---------|---------|
| `SkillLoader.load_all()` 加载所有 `.md` | Skill 分组 + L0 摘要按需加载 |
| 全部 Skill 注入 System Prompt (~5K tokens) | 仅注入匹配的 Skill 的 L1 概览 |
| 10 个 Skill 文件扁平存放 | 目录化: `skills/smart_home/`, `skills/dev/`, `skills/memory/` |

**当前 Skill 文件** (10 个):
```
skills/
├── homeassistant.md      → skills/smart_home/homeassistant.md
├── cron_scheduler.md     → skills/automation/cron_scheduler.md
├── python_sandbox.md     → skills/dev/python_sandbox.md
├── system_management.md  → skills/system/system_management.md
├── memory_management.md  → skills/memory/memory_management.md
├── memory/               → skills/memory/ (已分组)
│   ├── fact_extraction.md
│   ├── preference_capture.md
│   ├── semantic_search.md
│   └── exact_match.md
└── _template.md
```

**改进**:
1. 每个 Skill `.md` 的 YAML frontmatter 已有 `description`，这就是天然的 **L0**
2. `SkillLoader` 在启动时只加载 frontmatter (L0)，不读全文
3. `tool_router.route()` 时，同时匹配 Tools + Skills
4. 仅将匹配的 Skill 全文 (L2) 注入 System Prompt

**改动量**: `SkillLoader` 修改加载逻辑 (~30 行)，`agent.py` 修改注入逻辑 (~20 行)

---

### 3. Tool Router（工具路由）
| 当前状态 | 改进方案 |
|---------|---------|
| 扁平 Top-K (所有工具一起排) | 分组: `smart_home`, `dev`, `system` |
| 固定 Core Tools | 不变 |
| 评分 = cosine(query, description) | 评分 = α × 自身分数 + (1-α) × 组分数 |

**改动量**: `tool_router.py` 增加分组逻辑 (~40 行)

---

### 4. Prompt Builder（提示词构建）
| 当前状态 | 改进方案 |
|---------|---------|
| 静态拼接: Soul + User + Runtime | Tiered Assembly: Soul + L0 Skills → 按需注入 L2 |
| 所有 Skill 全文注入 | 仅注入路由匹配的 Skill 全文 |

**改动量**: `prompt_builder.py` 修改注入接口 (~20 行)

---

## Part B: Event Trigger System (电池提醒场景)

### 问题分析

用户需求: *"电量低于 2% 时提醒我"*

**当前限制**:
- `SchedulerService` 只支持 **Cron 定时任务**（每隔 X 分钟触发）
- 无法表达 **条件触发**（"当 X 满足条件时触发"）
- 无法 **监听 HA 状态变化**

### 方案对比

#### 方案 A: Cron 轮询 (简单但浪费)

```
                  ┌─────────────────┐
  每5分钟 ────────▶│  Cron Task       │
                  │  "检查电池电量"   │──▶ Agent ──▶ HA API ──▶ 判断 < 2%
                  └─────────────────┘              │
                                                   ▼
                                           电量 3%? → 不提醒 (浪费)
                                           电量 1%? → 提醒用户
```
- **优点**: 零新基础设施，复用现有 Scheduler + Agent
- **缺点**: 延迟最多 5 分钟；每次触发都消耗 LLM tokens；无法高频轮询

#### 方案 B: State Watch (HA 原生 Automation)

```
                  ┌─────────────────┐
  HA Automation ──▶│  State Trigger   │
  battery < 2%    │  (HA 内部)       │──▶ Webhook ──▶ Nexus Agent ──▶ 通知用户
                  └─────────────────┘
```
- **优点**: 实时、零延迟、不消耗 LLM tokens
- **缺点**: 需要在 HA 中创建 Automation（Agent 需要新工具 `create_automation`）

#### 方案 C: Hybrid Watch (推荐) ⭐

```
  ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
  │ State Watcher │────▶│ Condition Engine  │────▶│ Action Queue │
  │ (HA Events)  │     │ (battery < 2%)   │     │ (Notify User)│
  └──────────────┘     └──────────────────┘     └──────────────┘
        │                                              │
  SSE/WebSocket                                   MQ → Telegram
  from HA                                         (已有基础设施)
```

**新增组件**:
1. **StateWatcher**: 订阅 HA 的 WebSocket API `/api/websocket`，监听 `state_changed` 事件
2. **WatchRule 模型**: 定义触发规则
   ```python
   class WatchRule(SQLModel):
       entity_pattern: str    # "sensor.*.battery"
       condition: str         # "< 2"
       action: str           # "notify" | "agent_prompt"
       payload: dict         # {"message": "电池电量低于2%!"}
       cooldown_minutes: int  # 防止重复触发
   ```
3. **watch_entity Tool**: Agent 可以通过对话创建规则
   - 用户: "电量低于2%时提醒我"
   - Agent: 调用 `watch_entity(entity="sensor.phone_battery", condition="<2", action="notify")`

---

## Part C: Skill Designer (技能设计师)

`task.md` Phase 23 中已有 `[ ] **Designer**: Implement skill evolution logic`。

### 当前状态
- `SkillGenerator` 已可以生成 Skill Card（Phase 2）
- `learn_skill_rule` 工具已实现（Phase 12）
- 缺失: **自动进化循环**（Phase 7 提到但未实现）

### 设计方案
```
  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
  │ Audit Log   │────▶│ Error Scanner│────▶│ Designer AI  │
  │ (失败记录)   │     │ (每小时扫描)  │     │ (改进 Skill) │
  └─────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                           修改 Skill Card
                                           → 人工审核
                                           → 自动部署
```

---

## 优先级建议

| 优先级 | 项目 | 预计工作量 | 收益 |
|--------|------|-----------|------|
| **P0** | Skill 分层加载 (L0/L2) | 1-2h | 减少 ~3K tokens/turn |
| **P0** | Event Trigger (方案 C) | 4-6h | 解锁"电池提醒"等场景 |
| **P1** | Memory L0 摘要 | 2-3h | 减少检索噪音 |
| **P1** | Skill Designer Loop | 3-4h | 自动改进 Skill 质量 |
| **P2** | Tool Router 分组 | 2h | 提升路由精度 |

---

## Part D: Potential Skills from ClawHub (Future)

Research on `clawhub.ai` / OpenClaw ecosystem suggests the following high-value skills can be ported:

1.  **Playwright Scraper**:
    - **Capability**: Dynamic web interaction, JS rendering, form filling.
    - **Value**: Replacing static `read_url` with full browser automation.
    - **Implementation**: Wrap Python Playwright as a tool.

2.  **GitHub Integration**:
    - **Capability**: Issue tracking, PR reivew, code search.
    - **Value**: Self-evolution (Nexus improving its own code).

3.  **AgentMail / Communication**:
    - **Capability**: Sending emails, checking inbox.
    - **Value**: Asynchronous notifications beyond Telegram.

4.  **Project Management (Linear/Monday)**:
    - **Capability**: Managing tasks in external systems.
    - **Value**: Better task tracking than simple generic todo list.

*Note: Security audit required before porting community skills.*
