# Nexus Agent: Intelligent MCP Proxy & Large Response Handling

## The Challenge
MCP servers (like Home Assistant) can return massive JSON payloads (e.g., listing 100+ entities), which will instantly OOM the LLM context window.

## The Off-Loader Pattern (Adaptive Truncation)
1. **Tool Output Truncation**: `SessionManager.prune_tool_output()` intercepts raw tool outputs. If a response is > 2000 chars, it is replaced with a structural summary (e.g., "Type: List, 150 items. Preview IDs: [...]").
2. **The `python_sandbox` Bridge**: The LLM is instructed via system prompt to use the `python_sandbox` to iterate over or search through massive data locally, rather than trying to read it in the chat context.

## Traffic Governance
The proxy acts as an intermediary, caching frequent requests (like `get_entity_state`) to prevent slamming the underlying MCP service.
