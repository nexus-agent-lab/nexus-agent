from __future__ import annotations

from typing import Any, Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

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
    review_snapshot: dict[str, Any] | None


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
    def should_retry_tool_error(content: str) -> bool:
        if not content:
            return False

        lowered = content.lower()
        non_retryable_markers = (
            "permission denied",
            "internal system error",
            "tool '",
            "tool not found",
            "restricted for user",
        )
        if any(marker in lowered for marker in non_retryable_markers):
            return False

        return "error" in lowered

    @staticmethod
    def should_retry_classification(state: AgentState) -> bool:
        classification = state.get("last_classification") or {}
        selected_worker = state.get("selected_worker")
        attempts_by_worker = state.get("attempts_by_worker") or {}
        if selected_worker == "code_worker" and attempts_by_worker.get("code_worker", 0) >= 3:
            return False

        if classification:
            if classification.get("requires_handoff"):
                return False
            if classification.get("retryable"):
                return True

            next_action = classification.get("suggested_next_action")
            return next_action in {"retry_same_worker", "run_discovery", "switch_worker"}

        return False

    @staticmethod
    def prefers_chinese(messages: list[Any] | None) -> bool:
        for msg in reversed(messages or []):
            if isinstance(msg, HumanMessage):
                content = str(msg.content or "")
                return any("\u4e00" <= ch <= "\u9fff" for ch in content)
        return False

    @staticmethod
    def build_report_message(state: AgentState) -> str:
        classification = state.get("last_classification") or {}
        outcome = state.get("last_outcome") or {}
        summary = classification.get("user_facing_summary") or "Execution failed and needs intervention."
        detail = (
            classification.get("debug_summary")
            or outcome.get("raw_text")
            or "No additional error details were captured."
        )

        if len(detail) > 300:
            detail = detail[:300] + "..."

        if WorkerDispatcher.prefers_chinese(state.get("messages", [])):
            return (
                f"本次执行未能完成。\n原因：{summary}\n细节：{detail}\n下一步：请检查输入、权限或外部系统状态后再继续。"
            )

        return (
            f"The execution could not be completed.\n"
            f"Reason: {summary}\n"
            f"Details: {detail}\n"
            f"Next step: check the inputs, permissions, or external system state before trying again."
        )

    @staticmethod
    def build_verify_context(state: AgentState) -> dict[str, str]:
        classification = state.get("last_classification") or {}
        outcome = state.get("last_outcome") or {}
        execution_mode = state.get("execution_mode") or ""
        selected_worker = state.get("selected_worker") or ""
        selected_skill = state.get("selected_skill") or ""
        previous_hint = state.get("next_execution_hint") or ""
        detail = classification.get("debug_summary") or outcome.get("raw_text") or ""

        if detail and len(detail) > 240:
            detail = detail[:240] + "..."

        return {
            "worker": selected_worker,
            "skill": selected_skill,
            "execution_mode": execution_mode,
            "category": classification.get("category") or "",
            "reason": classification.get("user_facing_summary") or "",
            "detail": detail,
            "previous_hint": previous_hint,
        }

    @staticmethod
    def build_execution_history_entry(
        *,
        tool_name: str,
        selected_worker: str | None,
        selected_skill: str | None,
        execution_mode: str | None,
        next_execution_hint: str | None,
        outcome: dict | None,
        classification: dict | None,
    ) -> dict:
        outcome = outcome or {}
        classification = classification or {}
        return {
            "tool_name": tool_name,
            "worker": selected_worker,
            "skill": selected_skill,
            "execution_mode": execution_mode,
            "next_execution_hint": next_execution_hint,
            "status": outcome.get("status"),
            "fingerprint": outcome.get("fingerprint"),
            "classification": classification.get("category"),
            "next_action": classification.get("suggested_next_action"),
            "requires_handoff": classification.get("requires_handoff"),
        }

    @staticmethod
    def annotate_execution_history_entry(
        entry: dict,
        *,
        review_decision: dict | None,
        next_execution_hint: str | None,
    ) -> dict:
        review_decision = review_decision or {}
        updated = dict(entry)
        updated["next_execution_hint"] = next_execution_hint or updated.get("next_execution_hint")
        updated["verification_status"] = review_decision.get("verification_status")
        updated["review_mode"] = review_decision.get("execution_mode")
        verify_context = review_decision.get("verify_context") or {}
        if verify_context:
            updated["verify_reason"] = verify_context.get("reason")
        if review_decision.get("review_snapshot"):
            updated["review_snapshot"] = review_decision.get("review_snapshot")
        return updated

    @staticmethod
    def build_execution_history_lesson(state: AgentState) -> str | None:
        execution_history = state.get("execution_history") or []
        if not execution_history:
            return None

        latest = execution_history[-1]
        category = latest.get("classification") or "unknown"
        worker = latest.get("worker") or "unknown"
        tool_name = latest.get("tool_name") or "unknown_tool"
        next_hint = latest.get("next_execution_hint") or "unknown"
        verification_status = latest.get("verification_status") or "unknown"
        review_snapshot = latest.get("review_snapshot") or {}
        review_next_action = review_snapshot.get("next_action") or "unknown"
        verify_reason = review_snapshot.get("verify_reason")

        query = ""
        for message in state.get("messages", []):
            if isinstance(message, HumanMessage):
                query = str(message.content)[:50]
                break

        if not query:
            query = "recent task"

        lesson = (
            f"ROUTING LESSON: Query '{query}...' reached worker={worker}, tool={tool_name}, "
            f"classification={category}, next_hint={next_hint}, verification={verification_status}, "
            f"review_next_action={review_next_action}. "
            "Prefer similar routing and recovery handling for comparable requests."
        )
        if verify_reason:
            lesson += f" Reviewer note: {verify_reason}."
        return lesson

    @staticmethod
    def build_experience_replay_lesson(state: AgentState) -> str | None:
        messages = state.get("messages", [])
        retry_count = state.get("retry_count", 0)
        search_count = state.get("search_count", 0)

        lesson = WorkerDispatcher.build_execution_history_lesson(state)
        if search_count > 0 and messages:
            return (
                f"ROUTING LESSON: Query '{messages[0].content[:50]}...' required additional tool searching. "
                "Ensure prerequisite discovery tools are loaded."
            )
        if retry_count > 0 and lesson is None and messages:
            return (
                f"ROUTING LESSON: Query '{messages[0].content[:50]}...' failed initially and required reflexion. "
                "Check tool arguments and permissions."
            )
        return lesson

    @staticmethod
    def build_review_snapshot(
        state: AgentState,
        *,
        verification_status: str | None,
        execution_mode: str | None = None,
        verify_context: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        classification = state.get("last_classification") or {}
        snapshot: dict[str, Any] = {
            "worker": state.get("selected_worker"),
            "skill": state.get("selected_skill"),
            "execution_mode": execution_mode or state.get("execution_mode"),
            "verification_status": verification_status,
            "classification": classification.get("category"),
            "next_action": classification.get("suggested_next_action"),
            "requires_handoff": classification.get("requires_handoff"),
            "next_execution_hint": state.get("next_execution_hint"),
        }
        verify_context = verify_context or {}
        if verify_context.get("reason"):
            snapshot["verify_reason"] = verify_context.get("reason")
        return snapshot

    @staticmethod
    def build_code_repair_message(state: AgentState, retry_count: int) -> str:
        classification = state.get("last_classification") or {}
        outcome = state.get("last_outcome") or {}
        summary = classification.get("user_facing_summary") or "Code execution failed."
        detail = (
            classification.get("debug_summary")
            or outcome.get("raw_text")
            or "No additional error details were captured."
        )
        if detail and len(detail) > 300:
            detail = detail[:300] + "..."

        return (
            f"CODE REPAIR (Attempt {retry_count}/3): {summary}\n"
            f"Observed detail: {detail}\n"
            "Produce a materially different fix. Do not rerun the same code unchanged. "
            "Prefer a narrower, safer repair before calling tools again."
        )

    @staticmethod
    def build_reflexion_message(state: AgentState, *, retry_count: int) -> tuple[str, list[str]]:
        messages = state.get("messages") or []
        last_message = messages[-1] if messages else None

        failures = []
        classification = state.get("last_classification") or {}
        if classification:
            failures.append(
                classification.get("debug_summary") or classification.get("user_facing_summary") or "Unknown failure"
            )

        if isinstance(last_message, ToolMessage) and WorkerDispatcher.should_retry_tool_error(last_message.content):
            failures.append(last_message.content)

        critique = (
            f"REFLECTION (Attempt {retry_count}/3): The previous tool execution failed with: {failures}. "
            f"Please analyze why this happened (e.g., wrong arguments, missing permissions) "
            f"and try a different approach or correct the arguments. "
            f"Do not repeat the exact same invalid call."
        )
        return critique, failures

    @staticmethod
    def build_reflexion_patch(state: AgentState, *, retry_count: int) -> tuple[dict[str, Any], list[str]]:
        critique, failures = WorkerDispatcher.build_reflexion_message(state, retry_count=retry_count)
        return {
            "messages": [SystemMessage(content=critique)],
            "retry_count": retry_count,
            "reflexions": [critique],
        }, failures

    @staticmethod
    def build_report_failure_patch(state: AgentState) -> dict[str, Any]:
        return {
            "messages": [AIMessage(content=WorkerDispatcher.build_report_message(state))],
            "verification_status": "failed",
            "next_execution_hint": "report",
        }

    @staticmethod
    def build_verify_followup_patch(state: AgentState) -> dict[str, Any]:
        verify_context = WorkerDispatcher.build_verify_context(state)
        return {
            "execution_mode": "verify_followup",
            "next_execution_hint": "verify",
            "verification_status": "required",
            "verify_context": verify_context,
        }

    @staticmethod
    def build_clarify_followup_patch() -> dict[str, Any]:
        return {
            "messages": [
                SystemMessage(
                    content=(
                        "ASK USER MODE: Do not call more tools yet. "
                        "Ask one concise clarification question that will unblock the next step."
                    )
                )
            ],
            "execution_mode": "clarify_followup",
            "next_execution_hint": "ask_user",
        }

    @staticmethod
    def build_repair_followup_patch(state: AgentState, *, retry_count: int) -> dict[str, Any]:
        critique = WorkerDispatcher.build_code_repair_message(state, retry_count)
        return {
            "messages": [SystemMessage(content=critique)],
            "retry_count": retry_count,
            "execution_mode": "repair_followup",
            "next_execution_hint": "repair",
            "reflexions": [critique],
        }

    @staticmethod
    def build_followup_instructions(state: AgentState) -> list[str]:
        instructions: list[str] = []
        verification_status = state.get("verification_status")
        selected_worker = state.get("selected_worker")
        next_execution_hint = state.get("next_execution_hint")

        if verification_status == "failed":
            instructions.append(
                "VERIFICATION FAILED: Do not continue trying tools. "
                "Explain briefly what failed, why it could not be verified, "
                "and what user intervention or next step is needed."
            )

        if selected_worker == "code_worker" and next_execution_hint == "report":
            instructions.append(
                "CODE REPORT MODE: Do not execute more code or call more tools. "
                "Summarize the failure, include the most relevant error, and explain the next manual step."
            )

        if selected_worker == "code_worker" and next_execution_hint == "repair":
            instructions.append(
                "CODE REPAIR MODE: Propose a materially different fix from the previous failed attempt. "
                "Do not rerun the same code unchanged. Prefer using python_sandbox only after you change the approach."
            )

        if verification_status == "required":
            verify_context = state.get("verify_context") or {}
            verify_reason = verify_context.get("reason") or "Confirm the previous action result."
            verify_detail = verify_context.get("detail") or ""
            verify_worker = verify_context.get("worker") or selected_worker or "unknown"
            verify_skill = verify_context.get("skill") or state.get("selected_skill") or "unknown"
            instructions.append(
                "VERIFICATION REQUIRED: Do not finalize yet. "
                "Use an appropriate read/verify/discovery tool to confirm the previous action result.\n"
                f"Verification focus: {verify_reason}\n"
                f"Worker: {verify_worker}\n"
                f"Skill: {verify_skill}\n" + (f"Observed detail: {verify_detail}" if verify_detail else "")
            )

        return instructions

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
    def build_tool_retry_state(state: AgentState) -> dict[str, Any]:
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        tool_error_retryable = False

        if isinstance(last_message, ToolMessage):
            tool_error_retryable = WorkerDispatcher.should_retry_tool_error(last_message.content)

        return {
            "classification_retryable": WorkerDispatcher.should_retry_classification(state),
            "tool_error_retryable": tool_error_retryable,
        }

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
    def route_after_tool_with_runtime(
        state: AgentState,
    ) -> tuple[Literal["reflexion", "repair", "agent", "report", "__end__"], dict[str, Any]]:
        retry_state = WorkerDispatcher.build_tool_retry_state(state)
        route = WorkerDispatcher.route_after_tool(
            state,
            classification_retryable=retry_state["classification_retryable"],
            tool_error_retryable=retry_state["tool_error_retryable"],
        )
        return route, retry_state

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
    def route_after_review_with_runtime(
        state: AgentState,
    ) -> tuple[Literal["reflexion", "repair", "agent", "verify", "clarify", "report", "__end__"], dict[str, Any]]:
        fallback_route, retry_state = WorkerDispatcher.route_after_tool_with_runtime(state)
        route = WorkerDispatcher.route_after_review(state, fallback_route=fallback_route)
        return route, {"fallback_route": fallback_route, **retry_state}

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
        verification_status = review_patch.get("verification_status")
        execution_mode = "review_prepare"
        verify_context = state.get("verify_context")
        return WorkerExecutionDecision(
            selected_worker=review_patch.get("selected_worker"),
            execution_mode=execution_mode,
            active_tool_names=[],
            verification_status=verification_status,
            next_execution_hint=state.get("next_execution_hint"),
            verify_context=verify_context,
            review_snapshot=WorkerDispatcher.build_review_snapshot(
                state,
                verification_status=verification_status,
                execution_mode=execution_mode,
                verify_context=verify_context,
            ),
        )
