from __future__ import annotations

from typing import Any

from app.core.state import AgentState
from app.core.tool_catalog import ToolCatalog
from app.core.trace_logger import trace_logger
from app.core.worker_graphs.code_worker import run_code_worker_step
from app.core.worker_graphs.reviewer_worker import run_reviewer_worker_step
from app.core.worker_graphs.skill_worker import run_skill_worker_step


class WorkerDispatcher:
    """
    Compatibility dispatcher for phased migration to worker-based execution.

    Current scope:
    - select worker-specific tool preparation entrypoint
    - invoke reviewer preparation hook after classification

    Future scope:
    - own true worker subgraph dispatch instead of merely preparing state
    """

    @staticmethod
    async def prepare_tools(
        state: AgentState,
        available_tools: list[Any],
        matched_skills: list[dict],
        fallback_worker: str | None = None,
    ) -> tuple[list[Any], str | None]:
        selected_worker = state.get("selected_worker") or fallback_worker

        if selected_worker == "skill_worker":
            worker_patch = await run_skill_worker_step(state, available_tools, matched_skills)
            tool_names = worker_patch.get("active_tool_names", [])
            tools = ToolCatalog(available_tools).tools_by_names(tool_names)
        elif selected_worker == "code_worker":
            worker_patch = await run_code_worker_step(state, available_tools)
            tool_names = worker_patch.get("active_tool_names", [])
            tools = ToolCatalog(available_tools).tools_by_names(tool_names)
        else:
            tools = ToolCatalog(available_tools).filter_for_worker(selected_worker, matched_skills)

        trace_logger.log_wire_event(
            "worker_dispatch.prepare",
            trace_id=str(state.get("trace_id", "")),
            summary="Prepared tools through worker dispatcher.",
            details={
                "selected_worker": selected_worker,
                "tool_count": len(tools),
                "tools": [getattr(tool, "name", str(tool)) for tool in tools],
            },
        )
        return tools, selected_worker

    @staticmethod
    async def prepare_review(state: AgentState) -> dict:
        return await run_reviewer_worker_step(state)
