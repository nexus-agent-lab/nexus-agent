---
name: exact_match
domain: memory
skill_type: retrieval
description: 精确关键词匹配，适用于查找具体信息
intent_keywords: ["是什么", "密码", "邮箱", "地址", "what is", "password", "email", "address"]
version: 1
---

# Exact Match Retrieval Skill

## Purpose
Use keyword/SQL-based search for precise queries.

## Strategy
- Used when query contains specific identifiers
- Searches content field directly with LIKE/ILIKE
- Good for: "what's my password", "my email address"

## Implementation
```python
# Direct content search (pseudo-code)
statement = select(Memory).where(
    Memory.user_id == user_id,
    Memory.content.ilike(f"%{keyword}%")
)
```

## When to Use
- Query asks for specific value (password, email, API key)
- Query contains identifiable keywords
- Semantic search might return too many irrelevant results
