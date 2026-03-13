from __future__ import annotations

from typing import Any

from app.core.state import AgentState
from app.core.tool_catalog import ToolCatalog
from app.core.trace_logger import trace_logger
from app.core.worker_graphs.shared_execution import ToolExecutionPatch, execute_tool_call_generic


def prepare_code_worker_tools(state: AgentState, available_tools: list[Any]) -> list[Any]:
    """
    Build a code-scoped toolbelt for future `code_worker` subgraphs.

    The migration target is to centralize code execution logic here instead of
    leaving it inside the monolithic agent node.
    """
    catalog = ToolCatalog(available_tools)
    tools = catalog.filter_for_worker("code_worker", matched_skills=[])

    trace_logger.log_wire_event(
        "code_worker.prepare",
        trace_id=str(state.get("trace_id", "")),
        summary="Prepared code worker toolbelt.",
        details={
            "selected_worker": "code_worker",
            "tool_count": len(tools),
            "tools": [getattr(tool, "name", str(tool)) for tool in tools],
        },
    )
    return tools


async def run_code_worker_step(state: AgentState, available_tools: list[Any]) -> dict:
    """
    Minimal state-patch skeleton for future code execution subgraphs.
    """
    tools = prepare_code_worker_tools(state, available_tools)
    return {
        "selected_worker": "code_worker",
        "active_tool_names": [getattr(tool, "name", str(tool)) for tool in tools],
    }


async def execute_code_worker_tool_call(
    state: AgentState,
    *,
    tool_name: str,
    tool_call_id: str,
    tool_args: dict[str, Any],
    tool_to_call: Any,
    user: Any,
    trace_id: Any,
) -> ToolExecutionPatch:
    trace_logger.log_wire_event(
        "code_worker.execute",
        trace_id=str(state.get("trace_id", "")),
        summary="Dispatching tool call through code worker.",
        details={
            "tool_name": tool_name,
            "selected_worker": state.get("selected_worker") or "code_worker",
        },
    )
    return await execute_tool_call_generic(
        state,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        tool_args=tool_args,
        tool_to_call=tool_to_call,
        user=user,
        trace_id=trace_id,
        execution_mode="code_execute",
    )
