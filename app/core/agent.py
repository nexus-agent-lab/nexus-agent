import os
import uuid
from typing import Literal

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage

from app.core.state import AgentState
from app.tools.registry import get_tools
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

def create_agent_graph():
    llm = get_llm()

    tools = get_tools()
    tools_by_name = {t.name: t for t in tools}
    # Bind tools to LLM
    # Note: Ensure the provider supports OpenAI-format tool calling. 
    # GLM-4 and DeepSeek usually do.
    llm_with_tools = llm.bind_tools(tools)

    def call_model(state: AgentState):
        messages = state["messages"]
        try:
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        except Exception as e:
            # Handle API errors gracefully
            error_msg = f"Error calling LLM provider: {str(e)}"
            # Return a fast failure message to the user
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
            required_role = getattr(tool_to_call, "required_role", "user")
            
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
                # The Interceptor handles PENDING -> SUCCESS/FAILURE logging
                async with AuditInterceptor(
                    trace_id=trace_id,
                    user_id=user.id if user else None,
                    tool_name=tool_name,
                    tool_args=tool_args
                ):
                    prediction = tool_to_call.invoke(tool_args)
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
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node_with_permissions)
    workflow.set_entry_point("agent")
    
    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return "__end__"

    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    return workflow.compile()
