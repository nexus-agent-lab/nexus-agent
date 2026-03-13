from __future__ import annotations

from typing import Any

from app.core.state import AgentState
from app.core.tool_catalog import ToolCatalog
from app.core.trace_logger import trace_logger


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

    trace_logger.log_wire_event(
        "skill_worker.prepare",
        trace_id=str(state.get("trace_id", "")),
        summary="Prepared skill worker toolbelt.",
        details={
            "selected_skill": selected_skill,
            "selected_worker": selected_worker,
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
