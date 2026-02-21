# Optimization Plan: Dynamic Prompt & Robust Data Handling

Address critical issues regarding system prompt overfitting, token wastage, and fragile data handling in `python_sandbox` logic.

## 1. System Prompt Refactoring (The Universal Kernel)
**Goal**: Decouple the core agent from Home Assistant specifics and reduce token usage.

### [MODIFY] [agent.py](file:///Users/michael/work/nexus-agent/app/core/agent.py)
- **Replace** `BASE_SYSTEM_PROMPT` with the "Universal Kernel" structure:
  - **Core Protocols**: Autonomous Discovery, Data Governance (Big Data), Response Standards.
  - **Removed**: Hardcoded `AVAIABLE TOOLSETS` (LLM sees tools via API).
  - **Dynamic Injection**: Keep `MCPManager` hook for domain-specific rules (e.g., HA "don't guess IDs").

## 2. Middleware "Teacher" Mode (Fixing String Matching Trap)
**Goal**: Force the Agent to write robust, structured Python code instead of blind string matching.

### [MODIFY] [mcp_middleware.py](file:///Users/michael/work/nexus-agent/app/core/mcp_middleware.py)
- **Enhanced System Alert**: When intercepting large outputs, provide a "Code Guide":
  - Explicitly state file format (JSON List).
  - Mandate `json.load()`.
  - Require searching both `entity_id` and `attributes.friendly_name`.
  - Suggest `.lower()` and `.replace(' ', '_')` for fuzzy matching.

## 3. Data Source Verification
**Goal**: Ensure `list_entities` actually returns rich metadata (friendly names) for the new logic to work.

### [VERIFY] [mcp-homeassistant]
- Check `list_entities` implementation in the MCP server to ensure it includes `attributes`. (User has local access, but I assume standard HA API returns this. I will verify via `inspect_ha_raw.py` if needed).

## 4. Execution Plan
1.  **Refactor `agent.py`**: Apply the new Universal Kernel prompt.
2.  **Update `mcp_middleware.py`**: Inject the "Code Guide" into the truncation message.
3.  **Verification**: Run a complex query (e.g., "Find living room temperature") and observe if the generated Python code follows the new guidelines (JSON parsing vs string split).
