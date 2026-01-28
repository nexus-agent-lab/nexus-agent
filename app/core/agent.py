import os
import uuid
import logging
from typing import Literal

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage, SystemMessage, AIMessage

from app.core.state import AgentState
from app.core.audit import AuditInterceptor

BASE_SYSTEM_PROMPT = """You are Nexus, an advanced AI Operating System connecting the physical and digital worlds.

### CORE OPERATING PROTOCOLS
1. **AUTONOMOUS DISCOVERY**: 
   - You rarely know specific IDs (Device IDs, User IDs, Table Names) beforehand.
   - **MANDATORY**: Always use `list_*` or `search_*` tools FIRST to discover resources. Do NOT guess IDs.
   - **PROACTIVE**: If the user's intent is clear (e.g., "turn on lights"), find the target and execute. Do not ask for clarification unless necessary.

2. **DATA GOVERNANCE**:
   - **UNIFIED OUTPUT**: All tools return a JSON object: `{"type": "json" | "text" | "error", "content": ...}`.
   - **ACTION**: Always parse the `content` field.
   - If `type` is "json", use `content` directly.
   - If `type` is "text" and large string, write a Python script using `python_sandbox` to process/filter it.

3. **RESPONSE STANDARDS**:
   - **Language**: Strictly follow the user's language.
   - **Conciseness**: Return only the requested value (e.g., "25°C") without exposing internal IDs (like `sensor.lumi_weather`), unless debugging.
"""

def get_llm():
    """Configures and returns the LLM instance based on environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL", "gpt-4o")

    # CRITICAL DEBUG LOG
    logger.info(f"initializing LLM with: generated_url={base_url}, model={model_name}")

    if not api_key:
        print("Warning: LLM_API_KEY is not set.")
    
    # We use ChatOpenAI as the universal client for compatible APIs (GLM, DeepSeek, generic OpenAI)
    # If base_url is provided, it targets the custom provider.
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url, 
        temperature=0,
        streaming=True
    )

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
    
    return {
        "messages": [reflexion_msg], 
        "retry_count": retry_count,
        "reflexions": [critique]
    }

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
    mcp_instructions = MCPManager.get_system_instructions()
    
    dynamic_system_prompt = BASE_SYSTEM_PROMPT
    
    if mcp_instructions:
        dynamic_system_prompt += f"\n## SPECIFIC DOMAIN RULES\n{mcp_instructions}\n"


    async def call_model(state: AgentState):
        messages = list(state["messages"])
        
        # Ensure System Prompt is present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages.insert(0, SystemMessage(content=dynamic_system_prompt))
        elif isinstance(messages[0], SystemMessage) and "You are Nexus" not in messages[0].content:
            # If there's already a system message but it's not our base one, prepend ours
             messages[0] = SystemMessage(content=dynamic_system_prompt + "\n\n" + messages[0].content)

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
                                tool_calls=[{
                                    "name": data["name"],
                                    "args": data.get("arguments", {}) or data.get("parameters", {}),
                                    "id": f"patch_json_{id(response)}"
                                }]
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
                        code_match = re.search(r'```python\n(.*?)```', content, re.DOTALL)
                        if code_match:
                            match = code_match
                    
                    if match:
                        code_content = match.group(1).strip()
                        logger.warning(f"[Agent Patch] Recovered Regex Tool Call: python_sandbox")
                        response = AIMessage(
                            content="",
                            tool_calls=[{
                                "name": "python_sandbox",
                                "args": {"code": code_content},
                                "id": f"patch_regex_{id(response)}"
                            }]
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
                    if hasattr(msg, 'type') and msg.type == 'tool':
                        last_tool_msg = msg
                        break
                
                if last_tool_msg and "<<<OFFLOAD" in str(last_tool_msg.content):
                    import re
                    tool_content = str(last_tool_msg.content)
                    code_match = re.search(r'<<<CODE>>>\n(.*?)<<<END>>>', tool_content, re.DOTALL)
                    if code_match:
                        code = code_match.group(1).strip()
                        logger.warning(f"[Agent Patch C] Auto-extracted code from offload message")
                        response = AIMessage(
                            content="",
                            tool_calls=[{
                                "name": "python_sandbox",
                                "args": {"code": code},
                                "id": f"auto_extract_{id(response)}"
                            }]
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
            tool_to_call = tools_by_name.get(tool_name)
            tool_args = tool_call["args"]
            
            # 1. Permission Check
            required_role = getattr(tool_to_call, "required_role", "user")
            
            if required_role == "user" and hasattr(tool_to_call, "coroutine"):
                    required_role = getattr(tool_to_call.coroutine, "required_role", "user")

            if required_role == "admin" and (not user or user.role != "admin"):
                err_msg = f"Error: Permission denied. Tool '{tool_name}' requires '{required_role}' role."
                async with AuditInterceptor(
                    trace_id=trace_id,
                    user_id=user.id if user else None,
                    tool_name=tool_name,
                    tool_args=tool_args
                ) as audit_ctx:
                        raise PermissionError(err_msg)
                
                outputs.append(
                    ToolMessage(content=err_msg, name=tool_name, tool_call_id=tool_call["id"])
                )
                continue 

            # 2. Execution with Audit Interceptor
            result_str = ""
            try:
                if user:
                    tool_args["user_id"] = user.id

                tool_tags = getattr(tool_to_call, "tags", ["tag:safe"])
                if not tool_tags: tool_tags = ["tag:safe"]
                current_context = state.get("context", "home")
                user_role = user.role if user else "user"

                async with AuditInterceptor(
                    trace_id=trace_id,
                    user_id=user.id if user else None,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    user_role=user_role,
                    context=current_context,
                    tool_tags=tool_tags
                ):
                    prediction = await tool_to_call.ainvoke(tool_args)
                    result_str = str(prediction)
            
            except Exception as e:
                error_text = str(e)
                # 3. Error Sanitization
                # If it's a low-level infrastructure error, DO NOT pass it to the LLM to avoid confusion/loops.
                is_internal_error = any(k in error_text for k in [
                    "sqlalchemy", "asyncpg", "ConnectionRefused", "BrokenPipe", "OperationalError"
                ])
                
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
            log_preview = (result_str[:500] + '...') if len(str(result_str)) > 500 else result_str
            logger.info(f"TOOL OUTPUT ({tool_name}): {log_preview}")
            
            outputs.append(
                ToolMessage(content=result_str, name=tool_name, tool_call_id=tool_call["id"])
            )
        
        return {"messages": outputs}

    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve_memories", retrieve_memories)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node_with_permissions)
    workflow.add_node("reflexion", reflexion_node)
    
    workflow.set_entry_point("retrieve_memories")
    workflow.add_edge("retrieve_memories", "agent")

    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_conditional_edges("tools", should_reflect)
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
                yield {
                    "event": "tool_start", 
                    "data": {
                        "name": name,
                        "args": event["data"].get("input", {})
                    }
                }
            elif kind == "on_tool_end":
                output = event["data"].get("output")
                # Truncate for preview
                preview = (str(output)[:300] + "...") if len(str(output)) > 300 else str(output)
                yield {
                    "event": "tool_end",
                    "data": {
                        "name": name,
                        "result": preview
                    }
                }
            
            # 3. Final State
            elif kind == "on_chain_end" and name == "LangGraph":
                final_state = event["data"]["output"]
                if final_state and "messages" in final_state and final_state["messages"]:
                    last_msg = final_state["messages"][-1]
                    yield {"event": "final_answer", "data": getattr(last_msg, "content", "")}

    except Exception as e:
        logger.error(f"Error in astream_events: {e}", exc_info=True)
        yield {"event": "error", "data": str(e)}


