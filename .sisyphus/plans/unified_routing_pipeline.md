# Work Plan: Unified 4-Stage Routing Pipeline

## Objective
Implement the ultimate routing architecture to prevent 60s TTFT delays caused by context explosion. This integrates the Fast Brain (IntentRouter) with declarative Skill-to-Tool binding, allowing us to safely shrink the vector search funnel.

## Phase 1: Fast Brain Latency Monitoring
**Target**: `app/core/agent.py`
- Wrap `IntentRouter().decompose` in `time.perf_counter()`.
- Add an asynchronous call to `trace_logger.log_llm_call(..., phase="fast_brain", ...)` to record the exact decomposition time in the database and WireLog.
- Add an `asyncio.wait_for` timeout (e.g., 5 seconds) to `decompose` to prevent the Fast Brain from hanging the entire request if Ollama stalls. Fallback to `[last_human_msg]`.

## Phase 2: Skill-to-Tool Binding Implementation
**Target**: `app/core/tool_router.py`
- Add a new method `get_skill_bound_tools(self, matched_skills: List[dict]) -> List[Any]`.
- This method extracts the `required_tools` list from the metadata of all matched skills and retrieves the corresponding tool objects from `self.semantic_tools` and `self.core_tools`.

**Target**: `app/core/agent.py`
- Before calling `tool_router.route_multi`, extract `skill_bound_tools`.
- Merge the `skill_bound_tools` with the tools returned by `route_multi`, removing duplicates.

## Phase 3: Update Skill Metadata
**Target**: `skills/*.md`
- Update `homeassistant.md` frontmatter to include:
  `required_tools: ["list_entities", "get_entity", "entity_action", "call_service_tool"]`
- Update `web_browsing.md` frontmatter to include:
  `required_tools: ["browser_navigate", "browser_extract_text", "browser_screenshot"]`

## Phase 4: Context Compression (Shrink the Funnel)
**Target**: `app/core/config.py`
- Reduce `ROUTING_TOP_K` from 5 to 3.
**Target**: `app/core/tool_router.py`
- Reduce the hard limit on injected discovery tools from 5 to 2.

## Future Follow-Ups
- Add a lightweight readonly-query path for simple single-intent home queries, so `IntentRouter.decompose()` can be skipped when the request is clearly a direct lookup.
- Add Home Assistant query normalization for high-frequency readonly intents (temperature, humidity, battery, state) to reduce first-fail tool calls from malformed or noisy arguments.
- Investigate the unresolved MCP/StructuredTool null-argument bug where optional fields like `limit=None` / `detailed=None` still reach validation despite runtime stripping. Treat this as a dedicated debugging task, not a prompt-tuning task.
- Add tracing around the full tool invocation chain (`agent -> StructuredTool -> MCP middleware -> session.call_tool`) to locate where null optional fields are reintroduced or bypass the current sanitation layer.
- Keep these out of the current change set; finish observability first, then decide whether to implement them based on the new graph-step telemetry.

## Quality Assurance
- Run `bash scripts/dev_check.sh`.
