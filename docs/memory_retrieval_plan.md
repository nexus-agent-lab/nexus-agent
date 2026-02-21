# Implementation Plan - Memory Retrieval (query_memory)

Add the ability for the Agent to explicitly query its long-term memory (preferences, insights, knowledge) to improve personalization and transparency.

## Proposed Changes

### 1. Memory Manager Enhancements
**File**: `app/core/memory.py`
- **Method**: Add `list_memories(user_id, memory_type, limit)` to allow non-vector listing (e.g., "show me all my preferences").
- **Update**: Ensure `search_memory` can handle broad queries.

### 2. New Memory Tool
**File**: `app/tools/memory_tools.py`
- **Tool**: `query_memory(query: str, memory_type: str = None)`
- **Logic**: 
    - Use `memory_manager.search_memory` if `query` is provided.
    - Use `memory_manager.list_memories` if no `query` is provided (listing by type).
- **Description**: "Search or list your long-term memories, preferences, and saved insights."

### 3. Agent Integration
**File**: `app/core/agent.py`
- **Action**: Register the new `query_memory` tool in the agent graph.

## Verification Plan

### Automated Tests
- Create `tests/test_memory_retrieval.py` to verify:
    - Saving a preference and luego retrieving it via `query_memory`.
    - Listing all memories of a certain type.

### Manual Verification
- Ask the bot: "What do you know about my preferences?"
- Ask the bot: "Search my memories for 'coffee'."
