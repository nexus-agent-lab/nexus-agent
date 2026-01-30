---
name: Memory Management
description: Store and retrieve long-term user preferences, profile info, and insights.
intent_keywords: ["memory", "remember", "preference", "forget", "profile", "insight"]
---

# Memory Management Skill

This skill allows Nexus to maintain a long-term memory of user preferences, personal information, and key insights learned during interactions.

## Core Capabilities
- **`store_preference`**: Save personal details, habits, or favorites (e.g., "I like dark mode", "My birthday is May 5th").
- **`save_insight`**: Save broader lessons or complex context learned from the user's feedback or system behavior.
- **`forget_memory`**: Remove incorrect or outdated information by ID.

## Critical Rules
1. **PROACTIVE RETRIEVAL**: If a user asks "What do you know about me?" or "What are my preferences?", use `query_memory` with `memory_type="profile"`.
2. **SEMANTIC SEARCH**: Use `query_memory` with a specific `query` when looking for a particular fact shared in the past.

## Autonomous Memory Lifecycle (Crucial)
You are responsible for the accuracy of your long-term memory.
- **Auto-Identify**: If a user shares a new preference, hobby, or personal detail (e.g., "I started learning piano"), call `store_preference` immediately. Do not wait for a command.
- **Auto-Correct/Forget**: If a user contradicts a previous memory (e.g., "Actually, I hate coffee now"), follow these steps:
  1. Use `query_memory(query="coffee preference")` to find the relevant memory ID.
  2. Use `forget_memory(memory_id=...)` to remove the incorrect information.
  3. (Optional) Use `store_preference` to save the new correct information.
- **Verify before Guessing**: If you are about to suggest something based on a memory you're unsure about, query the memory first to confirm the details.

## Examples

### Example 1: Proactive Preference Query
**User**: "Can you suggest a theme for my dashboard?"
**Agent**: (Uses `query_memory(query="dashboard theme preference")`) 
**Tool Response**: "Found [profile] User prefers dark mode with blue highlights."
**Agent**: "Since you mentioned you prefer dark mode with blue highlights, I suggest using the 'Midnight Neon' theme."

### Example 2: Listing Insights
**User**: "What have we learned about the system performance lately?"
**Agent**: (Uses `query_memory(memory_type="reflexion")`)
**Tool Response**: "[reflexion] Users feel more productive when the interface is snappy."
**Agent**: "Based on our past reflections, we've noted that snappiness is a key factor in your productivity."
