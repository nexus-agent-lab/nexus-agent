# Nexus Agent: MemSkill Memory & Learning System

This document consolidates the architecture for the dynamic memory system and self-learning loop.

## 1. MemSkill Data Model
Memory skills determine how data is encoded into memory and retrieved.
* **id**: Primary Key
* **name**: Skill identifier (e.g., `ha_event_encoder`)
* **skill_type**: `encoding` (saving memory) or `retrieval` (querying)
* **intent_keywords**: Array of triggers for smart routing
* **prompt_template**: The LLM instruction for processing the data
* **version**: Integer tracking skill evolution
* **positive/negative_count**: Feedback metrics for the Designer loop

## 2. Session Compacting (P0.5)
To prevent Long Context KV-cache explosion:
* Triggered conditionally in `SessionManager.maybe_compact()`.
* Keeps the last `N` messages raw.
* Feeds older messages to the LLM to generate a rolling `SessionSummary`.
* Modifies `get_history` to return `[SessionSummary, ...N raw messages]`.

## 3. The Controller & Feedback Loop
* `MemoryController.select_skill()`: Uses keyword matching first, falls back to LLM if ambiguous.
* `MemoryController.prepare_context()`: Uses a Head+Tail strategy to truncate massive inputs without losing the start/end bounds.
* `record_feedback()`: Implicitly tracks if a skill resulted in a successful or failed action, powering the self-healing cycle.
