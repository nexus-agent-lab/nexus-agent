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

BASE_SYSTEM_PROMPT = """You are Nexus, an advanced AI Home Operating System.
Your goal is to assist the user by controlling their Smart Home and managing their digital life.

### INSTRUCTIONS
*   **ALWAYS** use the provided tools to answer questions about the environment or perform actions.
*   If you don't know the exact entity name (e.g. for Home Assistant), utilize list/search tools first.
*   **LANGUAGE**: ALWAYS reply in the same language as the user's request. (e.g., Use Chinese for Chinese queries).
*   Be concise and helpful.
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
        temperature=0
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

    # Group tools for cleaner System Prompt
    domains = {}
    for t in tools:
        # Extract domain from description "[domain] desc" or use "system"
        domain = "system"
        desc = t.description or ""
        if desc.startswith("[") and "]" in desc:
            end = desc.find("]")
            domain = desc[1:end]
            desc = desc[end+1:].strip()
        
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(t.name)

    domain_summary = []
    for domain, t_names in domains.items():
        domain_summary.append(f"### {domain.upper()} TOOLS\n" + ", ".join(t_names))
    
    tools_summary = "\n\n".join(domain_summary)
    
    dynamic_system_prompt = BASE_SYSTEM_PROMPT + f"\n\n## AVAIABLE TOOLSETS\n{tools_summary}\n"

    def call_model(state: AgentState):
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
            logger.info(f"LLM INPUT MESSAGES: {json.dumps(msgs_dicts, ensure_ascii=False)}")
            
            response = llm_with_tools.invoke(messages)
            
            # Debug: Log full output JSON
            resp_dict = message_to_dict(response)
            logger.info(f"LLM OUTPUT RAW JSON: {json.dumps(resp_dict, ensure_ascii=False)}")
            
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
