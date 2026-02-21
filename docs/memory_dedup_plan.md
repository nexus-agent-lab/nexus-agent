# Implementation Plan - Memory Deduplication

Prevent duplicate or semantically redundant memories from cluttering the database.

## Proposed Changes

### 1. Semantic Deduplication
**File**: `app/core/memory.py`
- **Method**: Update `add_memory` to perform a similarity search *before* insertion.
- **Logic**:
  - Embed the new content.
  - Search for existing memories with > 0.95 similarity (extremely close match).
  - If a detailed match exists, skip insertion or return the existing ID.
  - This prevents storing "I like red" if "I really like the color red" already exists.

### 2. Retrieval Optimization
**File**: `app/core/memory.py`
- **Goal**: Ensure search results don't return near-duplicates if they exist (though deduplication at write time is better).

### 3. Deletion Strategy
- **Context**: User asked if deletion is hard with vector DB.
- **Answer**: No. We use `pgvector` within Postgres, so deletion is a standard `DELETE FROM memory WHERE id = ...`. The vector index updates automatically (or lazily in HNSW). It is as easy as deleting a regular SQL row.

## Verification Plan

### Automated Tests
- **Script**: `tests/verify_memory_dedup.py`
- **Test Case 1**: Add "I like coffee".
- **Test Case 2**: Add "I like coffee" (exact match) -> Should detect duplicate.
- **Test Case 3**: Add "I really enjoy drinking coffee" (semantic match) -> Should detect high similarity.

### Manual Verification
- Ask the agent multiple similar things and verify via Dashboard that only one memory entry is created.
