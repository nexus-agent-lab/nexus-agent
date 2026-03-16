from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage

from app.core.result_classifier import ResultClassification
from app.core.state import AgentState
from app.core.tool_catalog import ToolCatalog
from app.core.tool_metadata import get_tool_metadata
from app.core.tool_router import CORE_TOOL_NAMES
from app.core.trace_logger import trace_logger
from app.core.worker_graphs.shared_execution import ToolExecutionPatch, execute_tool_call_generic

AMBIENT_QUERY_KEYWORDS = (
    "冷不冷",
    "室温",
    "家里温度",
    "房间温度",
    "温度最高",
    "温度最低",
    "最热",
    "最冷",
    "temperature",
)

AMBIENT_INCLUDE_KEYWORDS = (
    "客厅",
    "卧室",
    "主卧",
    "次卧",
    "书房",
    "儿童房",
    "餐厅",
    "房间",
    "室内",
    "环境",
    "home",
    "living room",
    "bedroom",
    "study",
    "indoor",
)

AMBIENT_EXCLUDE_KEYWORDS = (
    "冰箱",
    "冷冻",
    "冷藏",
    "热水器",
    "出水",
    "回水",
    "锅炉",
    "水温",
    "管道",
    "cpu",
    "设备内部",
    "freezer",
    "fridge",
    "refrigerator",
    "water heater",
    "boiler",
    "outlet",
    "pipe",
    "阳台",
)


def _is_explicit_homeassistant_action_request(state: AgentState) -> bool:
    if state.get("selected_skill") != "homeassistant":
        return False

    for message in reversed(state.get("messages") or []):
        if not isinstance(message, HumanMessage):
            continue
        content = str(message.content or "").lower()
        if any(
            token in content
            for token in (
                "打开",
                "关闭",
                "关掉",
                "开启",
                "打开它",
                "turn on",
                "turn off",
                "switch on",
                "switch off",
                "set ",
            )
        ):
            return True
        return False
    return False


def _is_homeassistant_ambient_temperature_request(state: AgentState) -> bool:
    if state.get("selected_skill") != "homeassistant":
        return False

    for message in reversed(state.get("messages") or []):
        if not isinstance(message, HumanMessage):
            continue
        content = str(message.content or "").lower()
        return any(token in content for token in AMBIENT_QUERY_KEYWORDS)

    return False


def _extract_result_payload(raw_text: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None]:
    try:
        parsed = json.loads(raw_text)
    except Exception:
        return None, None

    if isinstance(parsed, dict) and parsed.get("type") == "json" and isinstance(parsed.get("content"), list):
        return parsed, parsed["content"]
    if isinstance(parsed, list):
        return None, parsed
    return None, None


def _ambient_entity_text(entity: dict[str, Any]) -> str:
    attributes = entity.get("attributes") or {}
    return " ".join(
        str(part).lower()
        for part in (
            entity.get("entity_id", ""),
            attributes.get("friendly_name", ""),
            attributes.get("device_class", ""),
            attributes.get("unit_of_measurement", ""),
        )
        if part
    )


def _filter_ambient_temperature_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for entity in entities:
        haystack = _ambient_entity_text(entity)
        if any(token in haystack for token in AMBIENT_EXCLUDE_KEYWORDS):
            continue
        if not any(token in haystack for token in AMBIENT_INCLUDE_KEYWORDS):
            continue
        kept.append(entity)
    return kept or entities


def _apply_homeassistant_ambient_filter(
    state: AgentState,
    *,
    tool_name: str,
    execution_mode: str,
    execution_patch: ToolExecutionPatch,
) -> ToolExecutionPatch:
    if state.get("selected_skill") != "homeassistant":
        return execution_patch
    if tool_name != "list_entities" or execution_mode != "skill_discover":
        return execution_patch
    if not _is_homeassistant_ambient_temperature_request(state):
        return execution_patch

    outcome = execution_patch.get("outcome")
    message = execution_patch.get("message")
    if not outcome or not message:
        return execution_patch

    wrapper, entities = _extract_result_payload(outcome.get("raw_text", ""))
    if not entities:
        return execution_patch

    filtered_entities = _filter_ambient_temperature_entities(entities)
    if filtered_entities == entities:
        return execution_patch

    if wrapper is not None:
        raw_text = json.dumps({**wrapper, "content": filtered_entities}, ensure_ascii=False)
    else:
        raw_text = json.dumps(filtered_entities, ensure_ascii=False)

    execution_patch["outcome"] = {
        **outcome,
        "raw_text": raw_text,
        "structured_data": filtered_entities,
    }
    execution_patch["message"] = ToolMessage(content=raw_text, name=message.name, tool_call_id=message.tool_call_id)
    return execution_patch


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

    if next_hint == "act":
        filtered = []
        for tool in tools:
            metadata = get_tool_metadata(tool)
            operation_kind = metadata.get("operation_kind")
            if getattr(tool, "name", "") in CORE_TOOL_NAMES and getattr(tool, "name", "") != "python_sandbox":
                filtered.append(tool)
            elif operation_kind in {"act", "notify"}:
                filtered.append(tool)
        return filtered or tools, "act"

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
    execution_patch = _apply_homeassistant_ambient_filter(
        state,
        tool_name=tool_name,
        execution_mode=execution_mode,
        execution_patch=execution_patch,
    )
    classification, next_execution_hint = _postprocess_skill_classification(
        execution_patch.get("classification"),
        metadata=metadata,
        execution_mode=execution_mode,
        state=state,
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
    state: AgentState,
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

    if (
        execution_mode == "skill_discover"
        and classification.get("category") == "success"
        and _is_explicit_homeassistant_action_request(state)
    ):
        return (
            {
                **classification,
                "user_facing_summary": (
                    "Resource discovery succeeded for an explicit control request. "
                    "Execute the requested Home Assistant action before completing."
                ),
                "suggested_next_action": "complete",
            },
            "act",
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
