from __future__ import annotations

from typing import Any, Literal, TypedDict

from app.core.state import AgentState
from app.core.tool_catalog import ToolCatalog
from app.core.trace_logger import trace_logger
from app.core.worker_graphs.code_worker import execute_code_worker_tool_call, run_code_worker_step
from app.core.worker_graphs.reviewer_worker import run_reviewer_worker_step
from app.core.worker_graphs.shared_execution import ToolExecutionPatch, execute_tool_call_generic
from app.core.worker_graphs.skill_worker import execute_skill_worker_tool_call, run_skill_worker_step


class WorkerExecutionDecision(TypedDict, total=False):
    selected_worker: str | None
    execution_mode: Literal["direct", "skill_prepare", "code_prepare", "review_prepare", "skill_execute", "code_execute"]
    active_tool_names: list[str]


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
    async def execute_tool_call(
        state: AgentState,
        *,
        tool_name: str,
        tool_call_id: str,
        tool_args: dict[str, Any],
        tool_to_call: Any,
        user: Any,
        trace_id: Any,
    ) -> ToolExecutionPatch:
        selected_worker = state.get("selected_worker") or "chat_worker"
        if selected_worker == "skill_worker":
            return await execute_skill_worker_tool_call(
                state,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                tool_args=tool_args,
                tool_to_call=tool_to_call,
                user=user,
                trace_id=trace_id,
            )
        if selected_worker == "code_worker":
            return await execute_code_worker_tool_call(
                state,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                tool_args=tool_args,
                tool_to_call=tool_to_call,
                user=user,
                trace_id=trace_id,
            )
        return await execute_tool_call_generic(
            state,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_args=tool_args,
            tool_to_call=tool_to_call,
            user=user,
            trace_id=trace_id,
            execution_mode="direct",
        )

    @staticmethod
    async def prepare_tools(
        state: AgentState,
        available_tools: list[Any],
        matched_skills: list[dict],
        fallback_worker: str | None = None,
    ) -> tuple[list[Any], WorkerExecutionDecision]:
        selected_worker = state.get("selected_worker") or fallback_worker
        decision: WorkerExecutionDecision = {
            "selected_worker": selected_worker,
            "execution_mode": "direct",
            "active_tool_names": [],
        }

        if selected_worker == "skill_worker":
            worker_patch = await run_skill_worker_step(state, available_tools, matched_skills)
            tool_names = worker_patch.get("active_tool_names", [])
            tools = ToolCatalog(available_tools).tools_by_names(tool_names)
            decision["execution_mode"] = "skill_prepare"
            decision["active_tool_names"] = tool_names
        elif selected_worker == "code_worker":
            worker_patch = await run_code_worker_step(state, available_tools)
            tool_names = worker_patch.get("active_tool_names", [])
            tools = ToolCatalog(available_tools).tools_by_names(tool_names)
            decision["execution_mode"] = "code_prepare"
            decision["active_tool_names"] = tool_names
        else:
            tools = ToolCatalog(available_tools).filter_for_worker(selected_worker, matched_skills)
            decision["active_tool_names"] = [getattr(tool, "name", str(tool)) for tool in tools]

        trace_logger.log_wire_event(
            "worker_dispatch.prepare",
            trace_id=str(state.get("trace_id", "")),
            summary="Prepared tools through worker dispatcher.",
            details={
                "selected_worker": decision.get("selected_worker"),
                "execution_mode": decision.get("execution_mode"),
                "tool_count": len(tools),
                "tools": [getattr(tool, "name", str(tool)) for tool in tools],
            },
        )
        return tools, decision

    @staticmethod
    async def prepare_review(state: AgentState) -> WorkerExecutionDecision:
        review_patch = await run_reviewer_worker_step(state)
        return WorkerExecutionDecision(
            selected_worker=review_patch.get("selected_worker"),
            execution_mode="review_prepare",
            active_tool_names=[],
        )
