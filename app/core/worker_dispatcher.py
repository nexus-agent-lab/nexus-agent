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
    execution_mode: Literal[
        "direct",
        "skill_prepare",
        "code_prepare",
        "review_prepare",
        "skill_execute",
        "skill_discover",
        "skill_read",
        "skill_act",
        "skill_verify",
        "code_execute",
        "code_blocked",
        "verify_followup",
        "repair_followup",
    ]
    active_tool_names: list[str]
    verification_status: str | None
    next_execution_hint: str | None
    verify_context: dict[str, str] | None


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
    def route_after_agent(
        state: AgentState,
        *,
        has_tool_calls: bool,
    ) -> Literal["tools", "agent", "verify", "report", "__end__"]:
        if has_tool_calls:
            return "tools"
        if state.get("selected_worker") == "code_worker" and state.get("next_execution_hint") == "report":
            return "report"
        if state.get("verification_status") == "failed" and state.get("llm_call_count", 0) < 2:
            return "agent"
        if state.get("verification_status") == "required" and state.get("llm_call_count", 0) < 3:
            return "verify"
        return "__end__"

    @staticmethod
    def route_after_tool(
        state: AgentState,
        *,
        classification_retryable: bool,
        tool_error_retryable: bool,
    ) -> Literal["reflexion", "repair", "agent", "report", "__end__"]:
        selected_worker = state.get("selected_worker")
        attempts_by_worker = state.get("attempts_by_worker") or {}
        next_execution_hint = state.get("next_execution_hint")
        retry_count = state.get("retry_count", 0)

        if selected_worker == "code_worker" and next_execution_hint == "repair":
            return "repair"
        if selected_worker == "code_worker" and next_execution_hint == "report":
            return "report"
        if selected_worker == "code_worker" and next_execution_hint in {"verify", "ask_user", "complete"}:
            return "agent"
        if selected_worker == "code_worker" and attempts_by_worker.get("code_worker", 0) >= 3:
            return "agent"
        if classification_retryable:
            return "reflexion" if retry_count < 3 else "agent"
        if tool_error_retryable:
            return "reflexion" if retry_count < 3 else "agent"
        return "agent"

    @staticmethod
    def route_after_review(
        state: AgentState,
        *,
        fallback_route: str,
    ) -> Literal["reflexion", "repair", "agent", "verify", "clarify", "report", "__end__"]:
        verification_status = state.get("verification_status")
        next_execution_hint = state.get("next_execution_hint")
        selected_worker = state.get("selected_worker")
        classification = state.get("last_classification") or {}
        next_action = classification.get("suggested_next_action")

        if next_execution_hint == "report":
            return "report"
        if next_execution_hint == "ask_user":
            return "clarify"
        if verification_status == "failed" and (classification.get("requires_handoff") or next_action == "handoff"):
            return "report"
        if verification_status == "failed" and selected_worker == "code_worker":
            return "report"
        if verification_status == "failed" and classification.get("category") == "verification_failed":
            return "report"
        if verification_status == "required":
            return "verify"
        if selected_worker == "code_worker" and next_execution_hint == "repair":
            return "repair"
        if verification_status == "failed":
            return "agent"
        return fallback_route

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
            "next_execution_hint": state.get("next_execution_hint"),
            "verify_context": state.get("verify_context"),
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
            verification_status=review_patch.get("verification_status"),
            next_execution_hint=state.get("next_execution_hint"),
            verify_context=state.get("verify_context"),
        )
