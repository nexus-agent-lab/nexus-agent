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

def get_llm():
    """Configures and returns the LLM instance based on environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL", "gpt-4o")

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

def create_agent_graph(tools: list):
    llm = get_llm()

    # tools = get_tools() # Removed: Passed as arg
    tools_by_name = {t.name: t for t in tools}
    # Bind tools to LLM
    # Note: Ensure the provider supports OpenAI-format tool calling. 
    # GLM-4 and DeepSeek usually do.
    llm_with_tools = llm.bind_tools(tools)

    async def retrieve_memories(state: AgentState):
        user = state.get("user")
        if not user:
            return {"memories": []}
        
        # We query for the last user message to find relevant memories
        last_user_msg = ""
        for msg in reversed(state["messages"]):
            if msg.type == "user":
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

    def call_model(state: AgentState):
        messages = list(state["messages"])
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
            response = llm_with_tools.invoke(messages)
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
             # Should not happen based on edge logic, but safety check
             return {"messages": []}

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_to_call = tools_by_name.get(tool_name)
            tool_args = tool_call["args"]
            
            # 1. Permission Check
            # Check attribute on tool object, or on its coroutine (for Async StructuredTool)
            required_role = getattr(tool_to_call, "required_role", "user")
            
            # Special handling for LangChain StructuredTool derived from coroutine
            if required_role == "user" and hasattr(tool_to_call, "coroutine"):
                 # mcp.py attaches required_role to the coroutine function
                 required_role = getattr(tool_to_call.coroutine, "required_role", "user")

            if required_role == "admin" and (not user or user.role != "admin"):
                err_msg = f"Error: Permission denied. Tool '{tool_name}' requires '{required_role}' role."
                
                # Log Denied Access Attempt
                async with AuditInterceptor(
                    trace_id=trace_id,
                    user_id=user.id if user else None,
                    tool_name=tool_name,
                    tool_args=tool_args
                ) as audit_ctx:
                     # Force failure
                     raise PermissionError(err_msg)
                
                outputs.append(
                    ToolMessage(
                        content=err_msg,
                        name=tool_name,
                        tool_call_id=tool_call["id"],
                    )
                )
                continue 

            # 2. Execution with Audit Interceptor
            result_str = ""
            try:
                # Inject user_id into tool arguments if the tool signature expects it
                # For simplicity, we just inject it into the args dict. 
                # LangChain's StructuredTool will only pass it if it's in the args_schema or function signature.
                if user:
                    tool_args["user_id"] = user.id

                # The Interceptor handles PENDING -> SUCCESS/FAILURE logging
                async with AuditInterceptor(
                    trace_id=trace_id,
                    user_id=user.id if user else None,
                    tool_name=tool_name,
                    tool_args=tool_args
                ):
                    prediction = await tool_to_call.ainvoke(tool_args)
                    result_str = str(prediction)
            
            except Exception as e:
                # Interceptor's __aexit__ will catch this and log FAILURE
                result_str = f"Error executing tool: {e}"
            
            outputs.append(
                ToolMessage(
                    content=result_str,
                    name=tool_name,
                    tool_call_id=tool_call["id"],
                )
            )
        
        return {"messages": outputs}

    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve_memories", retrieve_memories)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node_with_permissions)
    
    workflow.set_entry_point("retrieve_memories")
    workflow.add_edge("retrieve_memories", "agent")
    
    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return "__end__"

    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    return workflow.compile()
