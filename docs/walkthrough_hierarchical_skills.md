# Walkthrough: Hierarchical Skill Loading (OpenViking Mode)

## Overview
We have transitioned from **Keyword-Based Skill Loading** to **Semantic (Vector) Routing** for skills. This aligns with the "OpenViking" architecture, prioritizing efficiency and accuracy.

### Key Benefits
- **Token Reduction**: Only relevant skills are injected into the context, rather than all summaries + keyword-triggered rules.
- **Accuracy**: Uses vector similarity (cosine) to understand user intent, not just keyword matching.
- **Efficiency**: Reuses the existing `ToolRouter`'s embedding model and in-memory numpy index. Zero extra API calls.

## Changes

### 1. Unified Semantic Router (`app/core/tool_router.py`)
- Renamed logic to support both Tools and Skills.
- Added `register_skills()`: Embeds skill descriptions into a numpy index (`skill_index`).
- Added `route_skills(query)`: Returns Top-K (default 3) skills matching the query above threshold (default 0.30).

### 2. Agent Logic (`app/core/agent.py`)
- **REMOVED**: `SkillLoader.load_summaries()` (L0 injection).
- **REMOVED**: Keyword-based intent matching loop.
- **ADDED**: `matched_skills = await tool_router.route_skills(routing_query)`
- **ADDED**: Injection of full rules for matched skills only.

### 3. Configuration (`app/core/config.py`)
- `SKILL_ROUTING_TOP_K = 3`
- `SKILL_ROUTING_THRESHOLD = 0.30`
- `DESIGNER_MIN_FEEDBACK`: Configurable via Env Var (default 10) for easier testing.

### 4. Application Lifecycle (`app/main.py`)
- Explicitly registers tools and skills with the router during startup (`lifespan`).

## Verification

### Automated Tests (`tests/unit/test_skill_routing.py`)
- **test_skill_routing_logic**:
  - Mocks embedding vectors.
  - Verifies "Turn on light" matches `home_assistant` skill (High Score).
  - Verifies "Random noise" matches NOTHING (Low Score).
- **test_skill_routing_permissions**:
  - Verifies Admin skills are NOT returned for User role, even if semantic match is perfect.

### Results
```
tests/unit/test_skill_routing.py::test_skill_routing_logic PASSED
tests/unit/test_skill_routing.py::test_skill_routing_permissions PASSED
```

## Next Steps
- Observe real-world performance using `DEBUG_WIRE_LOG=true`.
- Tune thresholds if necessary.
