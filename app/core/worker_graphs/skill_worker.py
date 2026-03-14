from __future__ import annotations

from typing import Any

from app.core.result_classifier import ResultClassification
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
    next_hint = state.get("next_execution_hint")

    if next_hint == "ask_user":
        return [], "clarify"

    if next_hint == "verify":
        filtered = []
        for tool in tools:
            metadata = get_tool_metadata(tool)
            operation_kind = metadata.get("operation_kind")
            if getattr(tool, "name", "") in CORE_TOOL_NAMES and getattr(tool, "name", "") != "python_sandbox":
                filtered.append(tool)
            elif operation_kind in {"verify", "read"} and not metadata.get("side_effect", False):
                filtered.append(tool)
        return filtered or tools, "verify"

    if next_hint == "discover":
        filtered = []
        for tool in tools:
            metadata = get_tool_metadata(tool)
            operation_kind = metadata.get("operation_kind")
            if getattr(tool, "name", "") in CORE_TOOL_NAMES:
                filtered.append(tool)
            elif operation_kind in {"discover", "read", "verify"} and not metadata.get("side_effect", False):
                filtered.append(tool)
        return filtered or tools, "discovery"

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
            if getattr(tool, "name", "") in CORE_TOOL_NAMES and getattr(tool, "name", "") != "python_sandbox":
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
    execution_patch = await execute_tool_call_generic(
        state,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        tool_args=tool_args,
        tool_to_call=tool_to_call,
        user=user,
        trace_id=trace_id,
        execution_mode=execution_mode,
    )
    classification, next_execution_hint = _postprocess_skill_classification(
        execution_patch.get("classification"),
        metadata=metadata,
        execution_mode=execution_mode,
    )
    execution_patch["classification"] = classification
    if next_execution_hint:
        execution_patch["next_execution_hint"] = next_execution_hint
    return execution_patch


def _postprocess_skill_classification(
    classification: ResultClassification | None,
    *,
    metadata: dict[str, Any],
    execution_mode: str,
) -> tuple[ResultClassification, str | None]:
    if classification is None:
        return (
            ResultClassification(
                category="non_retryable_runtime_error",
                retryable=False,
                should_switch_worker=False,
                requires_handoff=True,
                user_facing_summary="Skill execution did not return a usable result.",
                debug_summary="Skill worker did not receive a classification to post-process.",
                suggested_next_action="handoff",
            ),
            "report",
        )

    operation_kind = metadata.get("operation_kind", "read")
    side_effect = bool(metadata.get("side_effect"))

    if execution_mode == "skill_act" and classification.get("category") == "success":
        if classification.get("suggested_next_action") != "verify" and (
            side_effect or operation_kind in {"act", "notify", "transform"}
        ):
            return (
                {
                    **classification,
                    "user_facing_summary": "Action executed and should be verified before completion.",
                    "suggested_next_action": "verify",
                },
                "verify",
            )

    if execution_mode == "skill_discover" and classification.get("suggested_next_action") == "run_discovery":
        return (
            {
                **classification,
                "user_facing_summary": "Discovery did not find a matching resource. Ask for clarification instead of retrying discovery.",
                "suggested_next_action": "ask_user",
            },
            "ask_user",
        )

    if execution_mode == "skill_verify" and classification.get("category") == "invalid_input":
        return (
            {
                **classification,
                "category": "verification_failed",
                "retryable": False,
                "requires_handoff": False,
                "user_facing_summary": "Verification could not confirm the requested result.",
                "debug_summary": classification.get("debug_summary")
                or "Verification step returned invalid input or missing resource.",
                "suggested_next_action": "ask_user",
            },
            "report",
        )

    if classification.get("requires_handoff"):
        return (
            {
                **classification,
                "suggested_next_action": classification.get("suggested_next_action") or "handoff",
            },
            "report",
        )

    default_hint = {
        "verify": "verify",
        "run_discovery": "discover",
        "ask_user": "ask_user",
        "handoff": "report",
        "complete": "complete",
    }.get(classification.get("suggested_next_action"))

    return classification, default_hint
