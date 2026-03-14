from __future__ import annotations

from typing import Any

from app.core.result_classifier import ResultClassification
from app.core.state import AgentState
from app.core.tool_catalog import ToolCatalog
from app.core.tool_executor import ToolExecutionOutcome, build_tool_fingerprint
from app.core.tool_metadata import get_tool_metadata
from app.core.tool_router import CORE_TOOL_NAMES
from app.core.trace_logger import trace_logger
from app.core.worker_graphs.shared_execution import ToolExecutionPatch, execute_tool_call_generic


def prepare_code_worker_tools(state: AgentState, available_tools: list[Any]) -> list[Any]:
    """
    Build a code-scoped toolbelt for future `code_worker` subgraphs.

    The migration target is to centralize code execution logic here instead of
    leaving it inside the monolithic agent node.
    """
    catalog = ToolCatalog(available_tools)
    next_hint = state.get("next_execution_hint")
    if next_hint == "verify":
        verify_tools = [
            tool
            for tool in available_tools
            if (
                get_tool_metadata(tool).get("operation_kind") in {"verify", "read"}
                and not get_tool_metadata(tool).get("side_effect", False)
            )
        ]
        if verify_tools:
            tools = [
                tool
                for tool in available_tools
                if getattr(tool, "name", "") in CORE_TOOL_NAMES and getattr(tool, "name", "") != "python_sandbox"
            ] + verify_tools
        else:
            tools = [
                tool
                for tool in available_tools
                if getattr(tool, "name", "") in CORE_TOOL_NAMES or getattr(tool, "name", "") == "python_sandbox"
            ]
    else:
        tools = catalog.filter_for_worker("code_worker", matched_skills=[])

    if next_hint == "repair":
        tools = [
            tool
            for tool in tools
            if getattr(tool, "name", "") in CORE_TOOL_NAMES or getattr(tool, "name", "") == "python_sandbox"
        ] or tools
    elif next_hint == "verify":
        filtered = []
        for tool in tools:
            metadata = get_tool_metadata(tool)
            operation_kind = metadata.get("operation_kind")
            if getattr(tool, "name", "") in CORE_TOOL_NAMES:
                filtered.append(tool)
            elif operation_kind in {"verify", "read"} and not metadata.get("side_effect", False):
                filtered.append(tool)
        tools = filtered or tools
    elif next_hint == "report":
        tools = []

    trace_logger.log_wire_event(
        "code_worker.prepare",
        trace_id=str(state.get("trace_id", "")),
        summary="Prepared code worker toolbelt.",
        details={
            "selected_worker": "code_worker",
            "next_execution_hint": next_hint,
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
    fingerprint = build_tool_fingerprint(tool_name, args=tool_args, selected_skill=state.get("selected_skill"))
    if fingerprint in (state.get("blocked_fingerprints") or []):
        blocked_message = (
            "Error: Repeated code execution was blocked after previous failures. "
            "Generate a different fix instead of re-running the same code."
        )
        outcome = ToolExecutionOutcome(
            tool_name=tool_name,
            worker="code_worker",
            status="error",
            raw_text=blocked_message,
            structured_data=None,
            exception_text=blocked_message,
            latency_ms=0,
            fingerprint=fingerprint,
            metadata=get_tool_metadata(tool_to_call),
        )
        classification = ResultClassification(
            category="non_retryable_runtime_error",
            retryable=False,
            should_switch_worker=False,
            requires_handoff=True,
            user_facing_summary="Repeated code execution was blocked after previous failures.",
            debug_summary=blocked_message,
            suggested_next_action="handoff",
        )
        trace_logger.log_wire_event(
            "code_worker.blocked",
            trace_id=str(state.get("trace_id", "")),
            summary="Blocked repeated code execution fingerprint.",
            details={
                "tool_name": tool_name,
                "fingerprint": fingerprint[:12],
            },
        )
        return ToolExecutionPatch(
            message=None,
            outcome=outcome,
            classification=classification,
            execution_mode="code_blocked",
            next_execution_hint="report",
        )

    trace_logger.log_wire_event(
        "code_worker.execute",
        trace_id=str(state.get("trace_id", "")),
        summary="Dispatching tool call through code worker.",
        details={
            "tool_name": tool_name,
            "selected_worker": state.get("selected_worker") or "code_worker",
            "fingerprint": fingerprint[:12],
        },
    )
    execution_patch = await execute_tool_call_generic(
        state,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        tool_args=tool_args,
        tool_to_call=tool_to_call,
        user=user,
        trace_id=trace_id,
        execution_mode="code_execute",
    )
    classification, next_execution_hint = _postprocess_code_classification(execution_patch.get("classification"))
    execution_patch["classification"] = classification
    if next_execution_hint:
        execution_patch["next_execution_hint"] = next_execution_hint
    return execution_patch


def _postprocess_code_classification(
    classification: ResultClassification | None,
) -> tuple[ResultClassification, str | None]:
    if classification is None:
        return (
            ResultClassification(
                category="non_retryable_runtime_error",
                retryable=False,
                should_switch_worker=False,
                requires_handoff=True,
                user_facing_summary="Code execution did not return a usable result.",
                debug_summary="Code worker did not receive a classification to post-process.",
                suggested_next_action="handoff",
            ),
            "report",
        )

    category = classification.get("category")
    next_action = classification.get("suggested_next_action")

    if category == "success" and next_action == "complete":
        return (
            {
                **classification,
                "user_facing_summary": "Code execution finished and should be verified before completion.",
                "suggested_next_action": "verify",
            },
            "verify",
        )

    if category == "retryable_runtime_error":
        return classification, "repair"

    if category == "retryable_upstream_error":
        return classification, "retry"

    if category in {"non_retryable_runtime_error", "verification_failed"} or next_action == "handoff":
        return classification, "report"

    if category in {"invalid_input", "permission_denied", "wrong_tool_or_domain"}:
        return classification, "ask_user"

    return classification, {
        "verify": "verify",
        "retry_same_worker": "repair",
        "ask_user": "ask_user",
        "handoff": "report",
        "complete": "complete",
    }.get(next_action)
