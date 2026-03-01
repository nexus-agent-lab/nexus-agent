# Work Plan: Fix Home Assistant Routing & Fallback Logic (P0)

## Objective
Fix the persistent issue where the "Query Temperature" (查温度) command fails to discover the `list_entities` and `get_state` tools because of missing metadata tags causing harsh semantic down-ranking.

- [x] Phase 1: Tool Router Fallback Logic

**Target Files:**
- `app/core/tool_router.py`
- `app/core/config.py`

**Tasks:**
1. **Relax Routing Threshold:** In `app/core/config.py`, change `ROUTING_THRESHOLD` from `0.35` to `0.30` to allow for looser semantic matches when querying briefly.
2. **Improve Domain Multiplier (`app/core/tool_router.py`):**
   - Modify `_domain_multiplier()` to check the tool's raw `domain` attribute if `context_tags` are missing or empty.
   - If `current_context == "home"` and the tool's domain (via `_get_domain`) contains `homeassistant` or `smart_home`, grant it the `DOMAIN_AFFINITY["same"]` multiplier.
   - If no direct tags or domain string matches exist, return `DOMAIN_AFFINITY["adjacent"]` (1.0) rather than punishing the tool with `cross` (0.70). Only penalize if we *know* it belongs to a completely different context (e.g., system tool in a home context).

- [x] Phase 2: Harden HomeAssistant Skill

**Target File:** `app/skills/homeassistant.md`

**Tasks:**
1. **Add Critical Rule 0:** Insert the following as the absolute first rule under `## Critical Rules (MUST FOLLOW)`:
   `0. **Tool Prerequisite Rule**: For temperature/state queries, you MUST use a two-step process. First, ALWAYS call \`list_entities(domain='sensor', search_query='temperature')\`. Second, use the exact \`entity_id\` returned to call \`get_state()\`. NEVER guess an \`entity_id\`.`
2. **Expand Intent Keywords:** Update the YAML frontmatter `intent_keywords` array to include Chinese variations: `["温度", "灯", "设备", "状态", "空调", "家居", "客厅", "卧室", "查温度", "多少度", "冷不冷"]`.

- [x] Phase 3: Quality Assurance

- Run `bash scripts/dev_check.sh` to verify syntax and tests.
