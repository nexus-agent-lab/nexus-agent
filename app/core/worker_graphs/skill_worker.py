from __future__ import annotations

from typing import Any

from app.core.state import AgentState
from app.core.tool_catalog import ToolCatalog
from app.core.tool_metadata import get_tool_metadata
from app.core.tool_router import CORE_TOOL_NAMES
from app.core.trace_logger import trace_logger
from app.core.worker_graphs.shared_execution import ToolExecutionPatch, execute_tool_call_generic


def _filter_tools_for_skill_mode(state: AgentState, tools: list[Any]) -> tuple[list[Any], str]:
    intent_class = state.get("intent_class")
    classification = state.get("last_classification") or {}
    next_action = classification.get("suggested_next_action")

    if intent_class == "skill_discovery" or next_action == "run_discovery":
        filtered = []
        for tool in tools:
            metadata = get_tool_metadata(tool)
            operation_kind = metadata.get("operation_kind")
            if getattr(tool, "name", "") in CORE_TOOL_NAMES:
                filtered.append(tool)
            elif operation_kind in {"discover", "read", "verify"} and not metadata.get("side_effect", False):
                filtered.append(tool)
        return filtered or tools, "discovery"

    if next_action == "verify":
        filtered = []
        for tool in tools:
            metadata = get_tool_metadata(tool)
            operation_kind = metadata.get("operation_kind")
            if getattr(tool, "name", "") in CORE_TOOL_NAMES:
                filtered.append(tool)
            elif operation_kind in {"verify", "read"} and not metadata.get("side_effect", False):
                filtered.append(tool)
        return filtered or tools, "verify"

    return tools, "default"


def prepare_skill_worker_tools(state: AgentState, available_tools: list[Any], matched_skills: list[dict]) -> list[Any]:
    """
    Build a skill-scoped toolbelt for future `skill_worker` subgraphs.

    Today this reuses ToolCatalog. Later it can be moved behind a dedicated
    skill worker graph without changing the caller contract.
    """
    selected_skill = state.get("selected_skill")
    selected_worker = state.get("selected_worker") or "skill_worker"
    catalog = ToolCatalog(available_tools)
    tools = catalog.filter_for_worker(selected_worker, matched_skills)
    tools, toolbelt_mode = _filter_tools_for_skill_mode(state, tools)

    trace_logger.log_wire_event(
        "skill_worker.prepare",
        trace_id=str(state.get("trace_id", "")),
        summary="Prepared skill worker toolbelt.",
        details={
            "selected_skill": selected_skill,
            "selected_worker": selected_worker,
            "toolbelt_mode": toolbelt_mode,
            "tool_count": len(tools),
            "tools": [getattr(tool, "name", str(tool)) for tool in tools],
        },
    )
    return tools


async def run_skill_worker_step(state: AgentState, available_tools: list[Any], matched_skills: list[dict]) -> dict:
    """
    Minimal state-patch skeleton for future worker graph integration.

    This does not execute tools yet. It only materializes the worker-facing
    toolbelt and preserves worker selection in state.
    """
    tools = prepare_skill_worker_tools(state, available_tools, matched_skills)
    return {
        "selected_worker": "skill_worker",
        "active_tool_names": [getattr(tool, "name", str(tool)) for tool in tools],
    }


async def execute_skill_worker_tool_call(
    state: AgentState,
    *,
    tool_name: str,
    tool_call_id: str,
    tool_args: dict[str, Any],
    tool_to_call: Any,
    user: Any,
    trace_id: Any,
) -> ToolExecutionPatch:
    metadata = get_tool_metadata(tool_to_call)
    operation_kind = metadata.get("operation_kind", "read")
    execution_mode = {
        "discover": "skill_discover",
        "read": "skill_read",
        "act": "skill_act",
        "verify": "skill_verify",
        "notify": "skill_act",
        "transform": "skill_act",
    }.get(operation_kind, "skill_execute")

    trace_logger.log_wire_event(
        "skill_worker.execute",
        trace_id=str(state.get("trace_id", "")),
        summary="Dispatching tool call through skill worker.",
        details={
            "selected_skill": state.get("selected_skill"),
            "tool_name": tool_name,
            "operation_kind": operation_kind,
            "execution_mode": execution_mode,
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
        execution_mode=execution_mode,
    )
