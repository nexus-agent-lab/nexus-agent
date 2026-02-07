---
name: semantic_search
domain: memory
skill_type: retrieval
description: 语义向量搜索，适用于模糊查询
intent_keywords: ["之前", "提到过", "讨论", "关于", "about", "mentioned", "discussed"]
version: 1
---

# Semantic Search Retrieval Skill

## Purpose
Use vector similarity search for fuzzy/semantic queries.

## Strategy
- Default retrieval method
- Uses pgvector cosine similarity
- Good for: "what did we discuss about...", "something related to..."

## Implementation
```python
# This skill uses the existing MemoryManager.search_memory()
memories = await memory_manager.search_memory(user_id, query, limit=3)
```

## When to Use
- Query is vague or conceptual
- Looking for related information
- No specific identifiers mentioned
