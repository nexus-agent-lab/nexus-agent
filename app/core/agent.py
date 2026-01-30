import logging
import os
import uuid
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

from app.core.audit import AuditInterceptor
from app.core.session import SessionManager
from app.core.state import AgentState

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = """You are Nexus, an advanced AI Operating System connecting the physical and digital worlds.

### CORE OPERATING PROTOCOLS
1. **AUTONOMOUS DISCOVERY**:
   - You rarely know specific IDs (Device IDs, User IDs, Table Names) beforehand.
   - **MANDATORY**: Always use available discovery/search tools FIRST to locate resources.
     - Do NOT guess IDs.
   - **PROACTIVE**: If the user's intent is clear (e.g., "turn on lights"), find the target and execute.

2. **SKILL-BASED EXECUTION**:
   - Your capabilities are defined by the "LOADED SKILLS" section below.
   - **PRIORITY**: You MUST follow the specific rules and patterns defined in each Skill Card.
   - If a proper tool is missing, report the limitation.

3. **DATA & LOGIC HANDLING**:
   - **Large Outputs**: If a tool returns extensive text/JSON (e.g. >100 items), Do NOT output it directly. Use `python_sandbox` to filter/summarize.
   - **Calculations**: Use `python_sandbox` for any complex math or logic.

4. **DISCOVERY & ERROR RECOVERY**:
   - **Unknown Tools**: If you are unsure which tool to use, call `list_available_tools`.
   - **Unknown Arguments**: If you are unsure about a tool's arguments or schema, call `get_tool_details(tool_name)`.
   - **Do NOT Hallucinate**: Never invent tool names or arguments. Use discovery tools to find the truth.

5. **RESPONSE STANDARDS**:
   - **Language**: Strictly follow the user's language.
   - **Conciseness**: Return only the requested value or confirmation.
     - Avoid exposing internal IDs unless debugging.
"""


def get_llm():
    """Configures and returns the LLM instance based on environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL", "gpt-4o")

    # CRITICAL DEBUG LOG
    logger.info(f"initializing LLM with: base_url={base_url}, model={model_name}")

    if not api_key:
        print("Warning: LLM_API_KEY is not set.")

    # 针对 GLM-4.7-Flash 的特殊配置
    if "glm-4" in model_name.lower() and "flash" in model_name.lower():
        logger.info("Using optimized config for GLM-4.7-Flash")
        # 注意: num_ctx 应该在 Ollama 的 Modelfile 或启动时配置
        # OpenAI 兼容接口不支持通过 API 动态传递 num_ctx
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.1,  # Flash 模型建议值
            streaming=True,
        )

    # 其他模型使用默认配置
    return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, temperature=0, streaming=True)


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


def create_agent_graph(tools: list):
    llm = get_llm()
    tools_by_name = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    # Dynamic Instruction Injection from MCP Servers
    from app.core.mcp_manager import MCPManager
    from app.core.skill_loader import SkillLoader

    mcp_instructions = MCPManager.get_system_instructions()
    dynamic_system_prompt = BASE_SYSTEM_PROMPT

    # Layer 1: MCP-specific rules (legacy)
    if mcp_instructions:
        dynamic_system_prompt += f"\n## SPECIFIC DOMAIN RULES\n{mcp_instructions}\n"

    async def call_model(state: AgentState):
        messages = list(state["messages"])
        user = state.get("user")
        role = user.role if user else "guest"

        # 1. Load context-appropriate summaries and registry
        skill_summaries = SkillLoader.load_summaries(role=role)
        skill_registry = SkillLoader.load_registry_with_metadata(role=role)

        prompt_with_skills = dynamic_system_prompt
        # Layer 2: Skill Index (Summaries) - ALWAYS present so Agent knows what it CAN do (Role-specific)
        if skill_summaries:
            prompt_with_skills += (
                f"\n## AVAILABLE SKILLS (Overview)\n"
                f"You have the following skills available to your role ({role}). Detailed rules for a skill will be activated when relevant.\n"
                f"{skill_summaries}\n"
            )

        # 2. Capture User Intent for Dynamic Injection
        last_human_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_msg = str(msg.content).lower()
                break

        # 3. Dynamic Rule Activation (Role-aware)
        active_rules = []
        if last_human_msg:
            for skill in skill_registry:
                keywords = skill["metadata"].get("intent_keywords", [])
                # Activation Trigger: If any keyword matches the user message
                if any(kw.lower() in last_human_msg for kw in keywords):
                    logger.info(
                        f"🚀 [Dynamic Injection] Activating full rules for skill: {skill['name']} for role: {role}"
                    )
                    active_rules.append(f"### FULL RULES: {skill['name']}\n{skill['rules']}")

        final_system_prompt = prompt_with_skills
        if active_rules:
            final_system_prompt += "\n## ACTIVE SKILL RULES (CONTEXTUAL)\n" + "\n\n".join(active_rules) + "\n"

        # Ensure System Prompt is present with the latest dynamic rules
        if not messages or not isinstance(messages[0], SystemMessage):
            messages.insert(0, SystemMessage(content=final_system_prompt))
        elif isinstance(messages[0], SystemMessage) and "You are Nexus" not in messages[0].content:
            messages[0] = SystemMessage(content=final_system_prompt + "\n\n" + messages[0].content)
        else:
            # Update the existing system message with new dynamic rules if it was our base one
            messages[0] = SystemMessage(content=final_system_prompt)

        memories = state.get("memories", [])
        if memories:
            memory_context = "\n".join(memories)
            system_msg = SystemMessage(
                content=f"You have the following memories and preferences:\n{memory_context}\n"
                f"Use this context to personalize your response or avoid repeating mistakes."
            )
            # Find if there's already a system message to append to, or prepend this one
            if messages and isinstance(messages[0], SystemMessage):
                messages[0] = SystemMessage(content=messages[0].content + "\n\n" + system_msg.content)
            else:
                messages.insert(0, system_msg)

        try:
            # CRITICAL DEBUG: Log input messages (converted to list/dict for readability)
            import json

            from langchain_core.messages import message_to_dict

            msgs_dicts = [message_to_dict(m) for m in messages]
            logger.info(f"LLM INPUT MESSAGES:\n{json.dumps(msgs_dicts, ensure_ascii=False, indent=2)}")

            # DEBUG: Show what tools are in the "Tool Belt"
            tool_names = [t.name for t in tools]
            logger.info(f"LLM TOOL BELT ({len(tool_names)} tools): {tool_names}")

            response = await llm_with_tools.ainvoke(messages)

            # Debug: Log full output JSON
            resp_dict = message_to_dict(response)
            logger.info(f"LLM OUTPUT RAW JSON:\n{json.dumps(resp_dict, ensure_ascii=False, indent=2)}")

            # ======================================================
            # 🚑 【Universal Patch】Recover tool calls from plain text
            # Some local models (Qwen, Llama) output tool calls as text
            # instead of proper JSON. This patch recovers them.
            # ======================================================
            if not response.tool_calls:
                content = response.content.strip() if response.content else ""

                # Patch A: Markdown JSON block (```json {...} ```)
                if content.startswith("{") or "```json" in content:
                    try:
                        json_str = content.replace("```json", "").replace("```", "").strip()
                        data = json.loads(json_str)
                        if "name" in data:
                            logger.warning(f"[Agent Patch] Recovered JSON Tool Call: {data['name']}")
                            response = AIMessage(
                                content="",
                                tool_calls=[
                                    {
                                        "name": data["name"],
                                        "args": data.get("arguments", {}) or data.get("parameters", {}),
                                        "id": f"patch_json_{id(response)}",
                                    }
                                ],
                            )
                    except json.JSONDecodeError:
                        pass

                # Patch B: Pseudo-function text (python_sandbox(code))
                if not response.tool_calls and "python_sandbox" in content:
                    import re

                    # Match python_sandbox(...) with any content inside
                    match = re.search(r'python_sandbox\s*\(\s*["\']?(.*?)["\']?\s*\)', content, re.DOTALL)
                    if not match:
                        # Try matching triple-quoted code blocks
                        match = re.search(r'python_sandbox\s*\(\s*"""(.*?)"""\s*\)', content, re.DOTALL)
                    if not match:
                        # Try extracting code from markdown block after python_sandbox mention
                        code_match = re.search(r"```python\n(.*?)```", content, re.DOTALL)
                        if code_match:
                            match = code_match

                    if match:
                        code_content = match.group(1).strip()
                        logger.warning("[Agent Patch] Recovered Regex Tool Call: python_sandbox")
                        response = AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "python_sandbox",
                                    "args": {"code": code_content},
                                    "id": f"patch_regex_{id(response)}",
                                }
                            ],
                        )
            # ======================================================

            # ======================================================
            # 🔄 【Empty Response Reflexion】Force retry on silent failure
            # Patch C: Auto-extract <<<CODE>>> from offload tool message
            # ======================================================
            if not response.tool_calls and not (response.content and response.content.strip()):
                # Check if the last tool message contained offload alert
                last_tool_msg = None
                for msg in reversed(messages):
                    if hasattr(msg, "type") and msg.type == "tool":
                        last_tool_msg = msg
                        break

                if last_tool_msg and "<<<OFFLOAD" in str(last_tool_msg.content):
                    import re

                    tool_content = str(last_tool_msg.content)
                    code_match = re.search(r"<<<CODE>>>\n(.*?)<<<END>>>", tool_content, re.DOTALL)
                    if code_match:
                        code = code_match.group(1).strip()
                        logger.warning("[Agent Patch C] Auto-extracted code from offload message")
                        response = AIMessage(
                            content="",
                            tool_calls=[
                                {"name": "python_sandbox", "args": {"code": code}, "id": f"auto_extract_{id(response)}"}
                            ],
                        )
                    else:
                        logger.warning("[Agent Reflexion] Empty response after offload, retrying...")
                        nudge = SystemMessage(content="CALL python_sandbox NOW.")
                        messages.append(response)
                        messages.append(nudge)
                        response = llm_with_tools.invoke(messages)
                        resp_dict = message_to_dict(response)
                        logger.info(f"LLM RETRY OUTPUT: {json.dumps(resp_dict, ensure_ascii=False)}")
            # ======================================================

            return {"messages": [response]}
        except Exception as e:
            # Handle API errors gracefully
            error_msg = f"Error calling LLM provider: {str(e)}"
            return {"messages": [AIMessage(content=error_msg)]}

    async def tool_node_with_permissions(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        user = state.get("user")
        trace_id = state.get("trace_id", uuid.uuid4())

        outputs = []

        if not last_message.tool_calls:
            return {"messages": []}

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]

            # 🚑 【Universal Patch】Fix Malformed Tool Names (e.g. "forget_memoryforget_memory")
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
                error_msg = f"Error: Tool '{tool_name}' not found."
                logger.error(error_msg)
                outputs.append(ToolMessage(content=error_msg, name=tool_name, tool_call_id=tool_call["id"]))
                continue

            tool_args = tool_call["args"]

            # 1. Permission Check
            from app.core.auth_service import AuthService

            # Infer domain from tool name or tags (Simplification)
            # e.g. "homeassistant_get_state" -> domain="homeassistant" ??
            # For now, default to "standard" and rely on tool name blocking.

            if not AuthService.check_tool_permission(user, tool_name, domain="standard"):
                err_msg = (
                    f"Error: Permission denied. Access to tool '{tool_name}' is restricted for user '{user.username}'."
                )
                async with AuditInterceptor(
                    trace_id=trace_id, user_id=user.id if user else None, tool_name=tool_name, tool_args=tool_args
                ):
                    # We treat policy denial as a soft error for the agent to know,
                    # but we also raise exception to abort execution.
                    pass  # AuditInterceptor handles logging

                outputs.append(ToolMessage(content=err_msg, name=tool_name, tool_call_id=tool_call["id"]))
                continue

            # 2. Execution with Audit Interceptor
            result_str = ""
            try:
                if user:
                    tool_args["user_id"] = user.id

                tool_tags = getattr(tool_to_call, "tags", ["tag:safe"])
                if not tool_tags:
                    tool_tags = ["tag:safe"]
                current_context = state.get("context", "home")
                user_role = user.role if user else "user"

                async with AuditInterceptor(
                    trace_id=trace_id,
                    user_id=user.id if user else None,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    user_role=user_role,
                    context=current_context,
                    tool_tags=tool_tags,
                ):
                    prediction = await tool_to_call.ainvoke(tool_args)
                    result_str = str(prediction)

            except Exception as e:
                error_text = str(e)
                # 3. Error Sanitization
                # If it's a low-level infrastructure error, DO NOT pass it to the LLM to avoid confusion/loops.
                is_internal_error = any(
                    k in error_text
                    for k in ["sqlalchemy", "asyncpg", "ConnectionRefused", "BrokenPipe", "OperationalError"]
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

            # CRITICAL DEBUG LOG: Show what the tool actually returned
            log_preview = (result_str[:500] + "...") if len(str(result_str)) > 500 else result_str
            logger.info(f"TOOL OUTPUT ({tool_name}): {log_preview}")

            outputs.append(ToolMessage(content=result_str, name=tool_name, tool_call_id=tool_call["id"]))

        return {"messages": outputs}

    workflow = StateGraph(AgentState)

    # Logic Nodes
    # Logic Nodes
    workflow.add_node("retrieve_memories", retrieve_memories)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node_with_permissions)
    workflow.add_node("reflexion", reflexion_node)

    # Saving Nodes (Pass-through)
    workflow.add_node("save_agent", save_interaction_node)
    workflow.add_node("save_tool", save_interaction_node)

    # Flow
    workflow.set_entry_point("retrieve_memories")

    workflow.add_edge("retrieve_memories", "agent")

    # After Agent generates message, save it
    workflow.add_edge("agent", "save_agent")

    # Then decide where to go
    workflow.add_conditional_edges("save_agent", should_continue)

    # After Tools run, save the output, then reflect/loop back
    workflow.add_edge("tools", "save_tool")
    workflow.add_conditional_edges("save_tool", should_reflect)

    workflow.add_edge("reflexion", "agent")

    return workflow.compile()


async def stream_agent_events(graph, input_state: dict, config: dict = None):
    """
    Standardized wrapper for astream_events.
    Yields events for UI/Telegram consumption.
    """
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
                # Truncate for preview
                preview = (str(output)[:300] + "...") if len(str(output)) > 300 else str(output)
                yield {"event": "tool_end", "data": {"name": name, "result": preview}}

            # 3. Final State
            elif kind == "on_chain_end" and name == "LangGraph":
                final_state = event["data"]["output"]
                if final_state and "messages" in final_state and final_state["messages"]:
                    last_msg = final_state["messages"][-1]
                    yield {"event": "final_answer", "data": getattr(last_msg, "content", "")}

    except Exception as e:
        logger.error(f"Error in astream_events: {e}", exc_info=True)
        yield {"event": "error", "data": str(e)}
