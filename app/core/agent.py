import asyncio
import json
import logging
import os
import uuid
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, message_to_dict
from langgraph.graph import StateGraph

from app.core.audit import AuditInterceptor
from app.core.llm_utils import get_llm_client
from app.core.session import SessionManager
from app.core.state import AgentState

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = r"""You are Nexus, an AI Operating System connecting physical and digital worlds.

### PROTOCOLS
1. **DISCOVERY FIRST**: Never guess IDs. Use discovery/search tools to locate resources before acting.
2. **SKILL RULES**: Follow rules in LOADED SKILLS section. If a tool is missing, say so.
3. **LARGE DATA**: Use \`python_sandbox\` to filter/summarize large outputs (>100 items) or do calculations.
4. **NO HALLUCINATION**: Never invent tool names. Use \`list_available_tools\` if unsure.
5. **LANGUAGE**: Match the user's language. Be concise.
6. **MISSING CAPABILITIES**: If the user requests a capability you lack, assume it's a feature request and call \`submit_suggestion\` with type='feature_request'.
7. **DOMAIN VERIFICATION**: Before executing a tool, verify the tool's PURPOSE matches the user's INTENT. If the user asks about "system logs" but only "Home Assistant logs" tools are available, DO NOT substitute one for the other. Instead, inform the user: "I don't have system log access yet. I do have Home Assistant logs - would you like those instead?"
8. **KEYWORD ≠ INTENT**: The word "logs" can mean system logs, application logs, HA device logs, or audit logs. Always consider the CONTEXT of the request, not just the keyword match.
"""


async def retrieve_memories(state: AgentState):
    user = state.get("user")
    if not user:
        return {"memories": []}

    # We query for the last user message to find relevant memories
    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            last_user_msg = msg.content
            break

    if not last_user_msg:
        return {"memories": []}

    # Importing here to avoid potential circular deps
    from app.core.memory import memory_manager

    # Optimization: Skip memory retrieval for short messages (e.g. "hi", "ok", "stop")
    # or simple confirmations to save Embedding calls (which block for 200ms+)
    SKIP_PATTERNS = ["hi", "hello", "ok", "thanks", "thank you", "stop", "exit", "quit", "menu", "help"]
    if len(last_user_msg) < 10 or last_user_msg.strip().lower() in SKIP_PATTERNS:
        return {"memories": []}

    memories = await memory_manager.search_memory(user_id=user.id, query=last_user_msg)
    memory_strings = [f"[{m.memory_type}] {m.content}" for m in memories]

    logger.info(f"Retrieved {len(memory_strings)} memories for query '{last_user_msg}': {memory_strings}")

    return {"memories": memory_strings}


async def save_interaction_node(state: AgentState):
    """
    Saves the LAST message in the state to the history.
    This should be called after every major step (user input, AI response).
    """
    session_id = state.get("session_id")
    if not session_id:
        return {}

    messages = state["messages"]
    if not messages:
        return {}

    last_msg = messages[-1]

    # Determine role and type
    role, msg_type = "user", "human"
    if isinstance(last_msg, AIMessage):
        role, msg_type = "assistant", "ai"
    elif isinstance(last_msg, ToolMessage):
        role, msg_type = "tool", "tool"

    # Pruning check for ToolMessages
    content = last_msg.content
    is_pruned = False
    original_content = None

    if isinstance(last_msg, ToolMessage):
        content, is_pruned, original_content = await SessionManager.prune_tool_output(
            str(last_msg.content), getattr(last_msg, "name", "unknown")
        )

    await SessionManager.save_message(
        session_id=session_id,
        role=role,
        type=msg_type,
        content=str(content),
        tool_call_id=getattr(last_msg, "tool_call_id", None),
        tool_name=getattr(last_msg, "name", None),
        is_pruned=is_pruned,
        original_content=original_content if is_pruned else None,
    )

    # AUTO-COMPACTING: Trigger background compaction
    # Use create_task so we don't block the agent's response loop
    asyncio.create_task(SessionManager.maybe_compact(session_id))

    return {}


async def reflexion_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]

    failures = []
    if isinstance(last_message, ToolMessage):
        if "Error" in last_message.content or "Permission denied" in last_message.content:
            failures.append(last_message.content)

    retry_count = state.get("retry_count", 0) + 1

    critique = (
        f"REFLECTION (Attempt {retry_count}/3): The previous tool execution failed with: {failures}. "
        f"Please analyze why this happened (e.g., wrong arguments, missing permissions) "
        f"and try a different approach or correct the arguments. "
        f"Do not repeat the exact same invalid call."
    )

    reflexion_msg = SystemMessage(content=critique)

    return {"messages": [reflexion_msg], "retry_count": retry_count, "reflexions": [critique]}


def should_reflect(state: AgentState) -> Literal["reflexion", "agent", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]

    # Check if the last tool output was an error
    if isinstance(last_message, ToolMessage):
        content = last_message.content
        if "Error" in content or "Permission denied" in content:
            # Check retry limit
            if state.get("retry_count", 0) < 3:
                return "reflexion"
            else:
                return "agent"

    return "agent"


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"


async def experience_replay_node(state: AgentState):
    """
    JIT Experience Replay: Learns from tool routing failures and user corrections.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    # Only trigger if there was a detour (retry or search)
    retry_count = state.get("retry_count", 0)
    search_count = state.get("search_count", 0)

    if retry_count == 0 and search_count == 0:
        return {}

    # Logic: If the last message is from the assistant and it's successful,
    # we summarize the 'lesson learned'.
    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage) or not last_msg.content:
        return {}

    user = state.get("user")
    if not user:
        return {}

    try:
        from app.core.memory import memory_manager

        lesson = None
        if search_count > 0:
            lesson = f"ROUTING LESSON: Query '{messages[0].content[:50]}...' required additional tool searching. Ensure prerequisite discovery tools are loaded."
        elif retry_count > 0:
            lesson = f"ROUTING LESSON: Query '{messages[0].content[:50]}...' failed initially and required reflexion. Check tool arguments and permissions."

        if lesson:
            logger.info(f"Saving JIT Experience: {lesson}")
            await memory_manager.add_memory(
                user_id=user.id,
                content=lesson,
                memory_type="preference",
            )
    except Exception as e:
        logger.error(f"Experience Replay failed: {e}")

    return {}


def create_agent_graph(tools: list):
    # Standardized LLM initialization
    llm = get_llm_client()
    tools_by_name = {t.name: t for t in tools}

    # Dynamic Instruction Injection from MCP Servers
    from app.core.mcp_manager import MCPManager

    mcp_instructions = MCPManager.get_system_instructions()
    dynamic_system_prompt = BASE_SYSTEM_PROMPT

    # Layer 1: MCP-specific rules (legacy)
    if mcp_instructions:
        dynamic_system_prompt += f"\\n## SPECIFIC DOMAIN RULES\\n{mcp_instructions}\\n"

    async def call_model(state: AgentState):
        messages = list(state["messages"])
        user = state.get("user")
        user_role = user.role if user else "guest"

        # 0. Build Base System Prompt with User Context
        from app.core.prompt_builder import PromptBuilder
        from app.core.skill_loader import SkillLoader

        summaries = SkillLoader.load_summaries(role=user_role)
        # We use BASE_SYSTEM_PROMPT as the "Soul" — the immutable identity core
        base_prompt_with_context = PromptBuilder.build_system_prompt(
            user=user, soul_content=BASE_SYSTEM_PROMPT, skill_summaries=summaries
        )

        # 1. Prepare Semantic Routing Query (Noise-Reduced)
        # Find relevant context for routing (Role-Aware & Context-Aware)
        # We use the last few messages to understand conversational context
        # (e.g. "check logs" means different things after a home error vs. a system error)
        current_context = state.get("context", "home")
        search_count = state.get("search_count", 0)

        context_parts = []
        # Take up to 3 recent human messages (excluding System)
        human_msgs = [m for m in messages if isinstance(m, HumanMessage)][-3:]
        for msg in human_msgs:
            content = str(msg.content)
            # Truncate long messages to avoid noise in semantic matching
            if len(content) > 300:
                content = content[:300] + "..."
            context_parts.append(content)

        routing_query = f"Context: {current_context} | " + " | ".join(context_parts)

        # 2. Skill Routing (Hierarchical L0/L1/L2)
        from app.core.tool_router import tool_router

        prompt_with_skills = base_prompt_with_context
        matched_skills = await tool_router.route_skills(routing_query, role=user_role)

        if matched_skills:
            active_rules = []
            for i, s in enumerate(matched_skills):
                if i == 0:
                    # L2: Full Content for the most relevant skill (saves tokens vs. loading all)
                    content = s.get("full_content", s["rules"])
                    active_rules.append(f"### {s['name']} (PRIMARY)\\n{content}")
                else:
                    # L1: Critical Rules only for secondary matches
                    active_rules.append(f"### {s['name']} (SECONDARY)\\n{s['rules']}")
            prompt_with_skills += "\\n## ACTIVE SKILL RULES (CONTEXTUAL)\\n" + "\\n\\n".join(active_rules) + "\\n"

        final_system_prompt = prompt_with_skills

        # Ensure System Prompt is present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages.insert(0, SystemMessage(content=final_system_prompt))
        elif isinstance(messages[0], SystemMessage) and "You are Nexus" not in messages[0].content:
            messages[0] = SystemMessage(content=final_system_prompt + "\\n\\n" + messages[0].content)
        else:
            # Find if there's already a system message to append to, or prepend this one
            messages[0] = SystemMessage(content=final_system_prompt)

        memories = state.get("memories", [])
        if memories:
            memory_context = "\\n".join(memories)
            system_msg = SystemMessage(
                content=f"You have the following memories and preferences:\\n{memory_context}\\n"
                f"Use this context to personalize your response or avoid repeating mistakes."
            )
            # Find if there's already a system message to append to, or prepend this one
            if messages and isinstance(messages[0], SystemMessage):
                messages[0] = SystemMessage(content=messages[0].content + "\\n\\n" + system_msg.content)
            else:
                messages.insert(0, system_msg)

        # Dynamic Tool Routing
        from app.core.tool_router import CORE_TOOL_NAMES, tool_router

        _wire_log = os.getenv("DEBUG_WIRE_LOG", "false").lower() == "true"

        # --- Flow Trace Logging (Start) ---
        if _wire_log:
            last_msg_content = messages[-1].content if messages else "Unknown"
            if len(str(last_msg_content)) > 50:
                last_msg_content = str(last_msg_content)[:50] + "..."

            print(f'\\nUser Query: "{last_msg_content}"')
            print("  │")
            print("  ▼")
            print("① call_model (agent.py)")
            print("  │")

            sys_len = len(messages[0].content) if messages and isinstance(messages[0], SystemMessage) else 0
            print(f"  ├─ System Prompt Constructed (Length: {sys_len} chars)")
            print("  │")
            print(f'  ├─ tool_router.route("{routing_query[:50]}...", role={user_role}, context={current_context})')
            print("  │   ├─ Embedding Query -> Domain Affinity Scoring -> Collision Check")

        try:
            # Select relevant tools; pass user_role to enforce RBAC at the routing layer
            current_tools = await tool_router.route(routing_query, role=user_role, context=current_context)
            if not current_tools:
                # Fallback: give the LLM all role-permitted tools rather than nothing
                current_tools = [t for t in tools if tool_router._check_role(t, user_role)]

            if search_count >= 3:
                current_tools = [t for t in current_tools if t.name != "request_more_tools"]
                final_system_prompt += "\\n\\n## ⚠️ SEARCH LIMIT REACHED\\nYou have reached the limit for tool search retries (3/3). Use existing tools or inform user.\\n"
                messages[0] = SystemMessage(content=final_system_prompt)

        except Exception as e:
            logger.error(f"Error during tool routing: {e}")
            current_tools = tools

        # Bind only selected tools for this turn (not the full registry)
        llm_with_tools = llm.bind_tools(current_tools)

        if _wire_log:
            n_core = sum(1 for t in current_tools if t.name in CORE_TOOL_NAMES)
            n_sem = len(current_tools) - n_core
            print(f"  │   └─ Selected: {n_core} Core + {n_sem} Semantic = {len(current_tools)} Total")
            print("  │")
            print(f"  ├─ llm.bind_tools({len(current_tools)} Tools)")
            print("  │   └─ Converting to OpenAI Function Schemas")
            print("  │")
            print("  └─ llm.ainvoke(messages + tools) -> Sending to LLM")
            print("      │")
            print("      ▼")
            print("② LLM Request Body:")

            tool_schemas = llm_with_tools.kwargs.get("tools", [])
            msgs_dicts = [message_to_dict(m) for m in messages]
            req_body = {
                "model": os.getenv("LLM_MODEL", "unknown"),
                "messages": msgs_dicts[-2:],
                "tools": [t["function"]["name"] for t in tool_schemas],
            }
            print(json.dumps(req_body, ensure_ascii=False, indent=2))
            print("=" * 60 + "\\n")

        try:
            response = await llm_with_tools.ainvoke(messages)

            if _wire_log:
                resp_dict = message_to_dict(response)
                print("\\n" + "✅" * 15 + " [STRUCTURED] LLM RESPONSE BODY " + "✅" * 15)
                print(json.dumps(resp_dict, ensure_ascii=False, indent=2))
                print("=" * 100 + "\\n")

        except Exception as e:
            logger.error("Error calling LLM provider:", exc_info=True)
            return {"messages": [AIMessage(content=f"Error calling LLM provider: {str(e)}")]}

        return {"messages": [response]}

    async def tool_node_with_permissions(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        user = state.get("user")
        trace_id = state.get("trace_id", uuid.uuid4())
        outputs = []

        # Should not happen based on edge logic, but safety check
        if not last_message.tool_calls:
            return {"messages": []}

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]

            # 🚑 【Universal Patch】Fix Malformed Tool Names (e.g. "forget_memoryforget_memory")
            # This happens with some local models that repeat the tool name string.
            if tool_name not in tools_by_name:
                half_len = len(tool_name) // 2
                if len(tool_name) % 2 == 0 and tool_name[:half_len] == tool_name[half_len:]:
                    candidate = tool_name[:half_len]
                    if candidate in tools_by_name:
                        logger.warning(
                            f"[Agent Patch] Auto-corrected malformed tool name: '{tool_name}' -> '{candidate}'"
                        )
                        tool_name = candidate

            tool_to_call = tools_by_name.get(tool_name)
            if not tool_to_call:
                outputs.append(
                    ToolMessage(
                        content=f"Error: Tool '{tool_name}' not found.", name=tool_name, tool_call_id=tool_call["id"]
                    )
                )
                continue

            tool_args = tool_call["args"]

            # 1. Permission Check
            from app.core.auth_service import AuthService

            domain = "standard"
            if hasattr(tool_to_call, "metadata") and tool_to_call.metadata is not None:
                domain = tool_to_call.metadata.get("domain") or tool_to_call.metadata.get("category") or domain

            if not AuthService.check_tool_permission(user, tool_name, domain=domain):
                err_msg = f"Error: Permission denied. Access to tool '{tool_name}' is restricted for user '{user.username if user else 'guest'}'."
                async with AuditInterceptor(
                    trace_id=trace_id, user_id=user.id if user else None, tool_name=tool_name, tool_args=tool_args
                ):
                    pass
                outputs.append(ToolMessage(err_msg, name=tool_name, tool_call_id=tool_call["id"]))
                continue

            # 2. Execution with Audit Interceptor
            try:
                # Inject user_id into tool arguments if the tool expects it.
                # LangChain's StructuredTool will only use it if defined in args_schema.
                if user:
                    tool_args["user_id"] = user.id

                # The Interceptor handles Audit Logging (PENDING -> SUCCESS/FAILURE)
                async with AuditInterceptor(
                    trace_id=trace_id,
                    user_id=user.id if user else None,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    user_role=user.role if user else "user",
                    context=state.get("context", "home"),
                    tool_tags=getattr(tool_to_call, "tags", ["tag:safe"]),
                ):
                    # 🩹 Sanitize tool args: fix None values for typed params
                    # LLMs sometimes pass \`None\` for booleans/ints, causing Pydantic validation errors.
                    # This patch ensures defaults are used instead of None for critical types.
                    schema = getattr(tool_to_call, "args_schema", None)
                    if schema:
                        for field_name, field_info in schema.model_fields.items():
                            if field_name in tool_args and tool_args[field_name] is None:
                                anno = field_info.annotation
                                if anno is bool:
                                    tool_args[field_name] = (
                                        field_info.default if field_info.default is not None else False
                                    )
                                elif anno is int:
                                    tool_args[field_name] = field_info.default if field_info.default is not None else 0
                                elif anno is str:
                                    tool_args[field_name] = field_info.default if field_info.default is not None else ""

                    prediction = await tool_to_call.ainvoke(tool_args)
                    result_str = str(prediction)
            except Exception as e:
                error_text = str(e)
                # 3. Error Sanitization
                # If it's a low-level infrastructure error (DB/Network), DO NOT pass details to the LLM
                # to avoid confusion or infinite fixing loops.
                is_internal_error = any(
                    k in error_text for k in ["sqlalchemy", "asyncpg", "ConnectionRefused", "OperationalError"]
                )

                if is_internal_error:
                    # Log the specific crash for the admin
                    logger.error(f"CRITICAL SYSTEM ERROR in tool '{tool_name}': {error_text}", exc_info=True)
                    # Tell LLM generic info so it doesn't try to 'fix' code
                    result_str = "Error: Internal System Error. Please contact administrator."
                else:
                    # Logic errors (e.g. User Not Found) are useful for the LLM
                    logger.warning(f"Tool execution error ({tool_name}): {error_text}")
                    result_str = f"Error execution tool: {error_text}"

            outputs.append(ToolMessage(content=result_str, name=tool_name, tool_call_id=tool_call["id"]))

        return {"messages": outputs}

    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve_memories", retrieve_memories)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node_with_permissions)
    workflow.add_node("reflexion", reflexion_node)
    workflow.add_node("experience_replay", experience_replay_node)
    workflow.add_node("save_agent", save_interaction_node)
    workflow.add_node("save_tool", save_interaction_node)

    workflow.set_entry_point("retrieve_memories")
    workflow.add_edge("retrieve_memories", "agent")
    workflow.add_edge("agent", "save_agent")
    workflow.add_conditional_edges("save_agent", should_continue, {"tools": "tools", "__end__": "experience_replay"})
    workflow.add_edge("experience_replay", "__end__")
    workflow.add_edge("tools", "save_tool")
    workflow.add_conditional_edges("save_tool", should_reflect, {"reflexion": "reflexion", "agent": "agent"})
    workflow.add_edge("reflexion", "agent")

    return workflow.compile()


async def stream_agent_events(graph, input_state: dict, config: dict = None):
    """
    Standardized wrapper for astream_events.
    Yields events for UI/Telegram consumption.
    """
    if config is None:
        config = {}
    if "recursion_limit" not in config:
        config["recursion_limit"] = 20

    try:
        async for event in graph.astream_events(input_state, config=config, version="v2"):
            kind = event["event"]
            name = event.get("name", "Unknown")
            # 1. LLM Thoughts (Progressive Tokens)
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield {"event": "thought", "data": chunk.content}
            # 2. Tool Calls
            elif kind == "on_tool_start":
                yield {"event": "tool_start", "data": {"name": name, "args": event["data"].get("input", {})}}
            elif kind == "on_tool_end":
                output = event["data"].get("output")
                preview = (str(output)[:300] + "...") if len(str(output)) > 300 else str(output)
                yield {"event": "tool_end", "data": {"name": name, "result": preview}}
            # 3. Final State
            elif kind == "on_chain_end" and name == "LangGraph":
                final_state = event["data"]["output"]
                if final_state and "messages" in final_state and final_state["messages"]:
                    last_msg = final_state["messages"][-1]
                    yield {"event": "final_answer", "data": getattr(last_msg, "content", "")}
    except Exception as e:
        error_msg = str(e)
        if "recursion_limit" in error_msg.lower():
            error_msg = "⚠️ Agent 陷入了递归循环。已强制终止任务。"
        logger.error(f"Error in astream_events: {e}", exc_info=True)
        yield {"event": "error", "data": error_msg}
