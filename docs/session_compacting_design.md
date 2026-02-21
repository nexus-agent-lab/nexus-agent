# Session Auto-Compacting Design 📚

## 核心目标
解决 Context Window 随对话无限增长的问题，同时保留早期对话的关键信息。

## 策略：双层压缩

| 层级 | 触发条件 | 动作 | 目的 |
|------|----------|------|------|
| **L1** | 每次对话 | `get_history(limit=N)` | 保证 Recent Context 包含最新细节 |
| **L2** | 消息数 > X | 后台任务：生成摘要 + 归档旧消息 | 压缩历史，释放 Context |

---

## 数据库模型设计

### 1. SessionSummary 模型 (新增)

```python
class SessionSummary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    
    # 摘要内容
    summary: str = Field(sa_column=Column(Text))
    
    # 覆盖的消息范围
    start_msg_id: int
    end_msg_id: int
    msg_count: int
    
    created_at: datetime
```

### 2. SessionMessage 修改 (现有)

```python
class SessionMessage(SQLModel, table=True):
    # ... 现有字段 ...
    is_archived: bool = Field(default=False)  # True = 已被压缩进摘要
```

---

## 核心逻辑流程

### A. 压缩任务 (`compact_session`)

```python
async def compact_session(session_id: int, keep_last: int = 10):
    """后台运行：压缩旧消息"""
    # 1. 获取未归档消息总数
    count = await db.count(SessionMessage.where(session_id, is_archived=False))
    
    if count <= keep_last:
        return  # 不需要压缩
        
    # 2. 选出需要压缩的消息 (除了最后 N 条)
    to_compact = await db.fetch_oldest_unarchived(session_id, limit=count - keep_last)
    
    # 3. 生成摘要 (LLM)
    context = "\n".join([f"{m.role}: {m.content}" for m in to_compact])
    summary_text = await llm.summarize(context)
    
    # 4. 保存摘要 & 标记归档
    new_summary = SessionSummary(session_id=session_id, summary=summary_text, ...)
    await db.save(new_summary)
    await db.mark_as_archived([m.id for m in to_compact])
```

### B. 上下文组装 (`get_history_with_summary`)

```python
async def get_history_context(session_id: int, limit: int = 10) -> str:
    # 1. 获取所有历史摘要
    summaries = await db.fetch_all_summaries(session_id)
    summary_text = "\n".join([s.summary for s in summaries])
    
    # 2. 获取最近的未归档消息
    recent_msgs = await db.fetch_recent_unarchived(session_id, limit=limit)
    
    return f"""
## PREVIOUS CONTEXT SUMMARY
{summary_text}

## RECENT MESSAGES
{format_messages(recent_msgs)}
"""
```

---

## 实现步骤

1. **Model**: 创建 `SessionSummary` 表，更新 `SessionMessage`
2. **Logic**: 实现 `SessionManager.compact_session()`
3. **Trigger**:
   - 方式 A: 每次 `save_message` 后检查 (简单)
   - 方式 B: 定时任务 (复杂)
   - **建议**: 方式 A (Lazy Evaluation)
4. **Integration**: 修改 `agent.py` 使用新的 context 组装方法

---

## 风险控制

- **信息丢失**: 摘要可能丢失细节 → 提供 `query_history` 工具查原始记录
- **LLM 幻觉**: 摘要可能歪曲事实 → 在 System Prompt 强调摘要仅供参考
- **性能**: 压缩操作异步执行 (`asyncio.create_task`)，不阻塞主对话
