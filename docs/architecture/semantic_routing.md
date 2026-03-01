# Nexus Agent: Semantic Routing Design (V3)

This document describes the 3-Tier hybrid routing architecture to solve the "Vector Blindness" problem.

## Tier 1: Domain Affinity & Context Tags (Pre-emptive)
- **Problem**: Vectors understand keywords, not domain boundaries.
- **Solution**: 
  - Plugins define `context_tags` in `plugin_catalog.json` (e.g., `["home", "ha"]`).
  - `tool_router.py` applies a multiplier (e.g., `1.15x`) to tools matching the current context.
  - **Discovery Injection**: If the user is in the `home` context, foundational discovery tools (`list_entities`) are hard-injected into the payload, bypassing vector scores entirely.

## Tier 2: The Fast Brain (Intent Router)
- **Problem**: Cross-domain requests ("Turn off light AND log to Feishu") fail because the vector space averages out the embedding, missing one side.
- **Solution**: `app/core/intent_router.py`.
  - A fast, zero-tool LLM call decomposes the user query into distinct JSON intents.
  - The `SemanticToolRouter.route_multi()` then embeds each intent separately and takes the union of the Top-K tools.

## Tier 3: JIT Negative Reinforcement
- **Problem**: Repeated routing errors.
- **Solution**: `ExperienceReplay` node captures detours and saves them as `preference` memories ("Do not use X for Y").
