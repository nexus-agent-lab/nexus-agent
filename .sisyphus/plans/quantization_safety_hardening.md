# Execution Plan: Quantization Safety Hardening

**Context:** Local quantized models suffer from safety degradation and an increased propensity to hallucinate tool parameters when context windows grow or when pushed with complex prompts (as highlighted by the T-PTQ paper). This plan hardens the system prompt and tracks two architectural solutions (DualPath compaction and safety benchmarking) in the project roadmap.

## Phase 1: Prompt Hardening (P0) [COMPLETED]

**Target File:** `app/core/agent.py`

**Tasks:**
1. Locate the `BASE_SYSTEM_PROMPT` variable definition.
2. **Update Protocol Rule 4:** 
   Find the line:
   `4. **NO HALLUCINATION**: Never invent tool names. Use \`list_available_tools\` if unsure.`
   Replace it with the stronger, redundant directive:
   `4. **CRITICAL RULE**: DO NOT INVENT TOOL NAMES or ARGUMENTS. If you lack information or tools, STOP and ASK the user.`
3. **Add Security Section:**
   Immediately following the `### PROTOCOLS` section (but still inside the `BASE_SYSTEM_PROMPT` string), add a new specific section for security:
   ```text
   ### SECURITY & ALIGNMENT
   - STRICT COMPLIANCE: You must strictly adhere to your defined Role-Based Access Control (RBAC) and tool limits.
   - NO BYPASSING: Any attempt to bypass constraints, hallucinate unauthorized tool calls, or fabricate parameters is a severe security violation.
   ```

## Phase 2: Project Backlog Update (P1/P2)
**Target File:** `docs/priorities.md`

**Tasks:**
1. Open the project tracking file (`docs/priorities.md`) and append the following two Epics to the roadmap:

   * **Epic 1: Aggressive Tool Output Compaction (DualPath inspired) [P1]**
     * **Description:** Transform raw JSON tool outputs into clean, LLM-summarized facts *before* feeding them back into the LangGraph state. 
     * **Goal:** Save KV-Cache space, reduce context noise, and minimize the risk of quantized models degrading and hallucinating after large tool responses.
   
   * **Epic 2: Quantization-Aware Safety Benchmark (T-PTQ inspired) [P2]**
     * **Description:** Build a dedicated test suite (`tests/integration/test_safety_alignment.py`) to systematically test safety under quantization.
     * **Goal:** Automatically evaluate if local quantized models attempt to bypass RBAC, hallucinate tool parameters, or break alignment under complex prompt conditions and heavy context loads.
