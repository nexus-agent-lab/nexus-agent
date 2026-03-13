from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict, get_args, get_origin

from langchain_core.messages import ToolMessage

from app.core.audit import AuditInterceptor
from app.core.auth_service import AuthService
from app.core.result_classifier import ResultClassification, ResultClassifier
from app.core.state import AgentState
from app.core.tool_catalog import ToolCatalog
from app.core.tool_executor import ToolExecutionOutcome, build_tool_fingerprint
from app.core.tool_metadata import get_tool_metadata
from app.core.trace_logger import trace_logger
from app.core.worker_graphs.code_worker import run_code_worker_step
from app.core.worker_graphs.reviewer_worker import run_reviewer_worker_step
from app.core.worker_graphs.skill_worker import run_skill_worker_step

logger = logging.getLogger(__name__)
NONE_TYPE = type(None)


class WorkerExecutionDecision(TypedDict, total=False):
    selected_worker: str | None
    execution_mode: Literal["direct", "skill_prepare", "code_prepare", "review_prepare"]
    active_tool_names: list[str]


class ToolExecutionPatch(TypedDict, total=False):
    message: ToolMessage
    outcome: ToolExecutionOutcome
    classification: ResultClassification


def _unwrap_optional_annotation(annotation):
    if annotation in (None, NONE_TYPE):
        return None

    origin = get_origin(annotation)
    if origin is None:
        return annotation

    args = [arg for arg in get_args(annotation) if arg is not NONE_TYPE]
    if len(args) == 1:
        return args[0]

    return annotation


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
        worker = state.get("selected_worker") or "chat_worker"
        selected_skill = state.get("selected_skill")
        fingerprint = build_tool_fingerprint(tool_name, args=tool_args, selected_skill=selected_skill)
        metadata = get_tool_metadata(tool_to_call)

        domain = "standard"
        required_role = None
        allowed_groups = None
        if hasattr(tool_to_call, "metadata") and tool_to_call.metadata is not None:
            domain = tool_to_call.metadata.get("domain") or tool_to_call.metadata.get("category") or domain
            required_role = tool_to_call.metadata.get("required_role")
            allowed_groups = tool_to_call.metadata.get("allowed_groups")

        if not AuthService.check_tool_permission(
            user, tool_name, domain=domain, required_role=required_role, allowed_groups=allowed_groups
        ):
            err_msg = (
                f"Error: Permission denied. Access to tool '{tool_name}' is restricted for user "
                f"'{user.username if user else 'guest'}'."
            )
            async with AuditInterceptor(
                trace_id=trace_id, user_id=user.id if user else None, tool_name=tool_name, tool_args=tool_args
            ):
                pass

            outcome = ToolExecutionOutcome(
                tool_name=tool_name,
                worker=worker,
                status="error",
                raw_text=err_msg,
                structured_data=None,
                exception_text=err_msg,
                latency_ms=0,
                fingerprint=fingerprint,
                metadata=metadata,
            )
            classification = ResultClassifier.classify(outcome)
            return ToolExecutionPatch(
                message=ToolMessage(content=err_msg, name=tool_name, tool_call_id=tool_call_id),
                outcome=outcome,
                classification=classification,
            )

        try:
            if user:
                tool_args["user_id"] = user.id

            schema = getattr(tool_to_call, "args_schema", None)
            if schema:
                for field_name, field_info in schema.model_fields.items():
                    if field_name in tool_args and tool_args[field_name] is None:
                        anno = _unwrap_optional_annotation(field_info.annotation)
                        if not field_info.is_required():
                            tool_args.pop(field_name, None)
                        elif anno is bool:
                            tool_args[field_name] = field_info.default if field_info.default is not None else False
                        elif anno is int:
                            tool_args[field_name] = field_info.default if field_info.default is not None else 0
                        elif anno is str:
                            tool_args[field_name] = field_info.default if field_info.default is not None else ""

            async with AuditInterceptor(
                trace_id=trace_id,
                user_id=user.id if user else None,
                tool_name=tool_name,
                tool_args=tool_args,
                user_role=user.role if user else "user",
                context=state.get("context", "home"),
                tool_tags=getattr(tool_to_call, "tags", ["tag:safe"]),
            ):
                prediction = await tool_to_call.ainvoke(tool_args)
                result_str = str(prediction)

            outcome = ToolExecutionOutcome(
                tool_name=tool_name,
                worker=worker,
                status="success",
                raw_text=result_str,
                structured_data=None,
                exception_text=None,
                latency_ms=0,
                fingerprint=fingerprint,
                metadata=metadata,
            )
        except Exception as exc:
            error_text = str(exc)
            is_internal_error = any(
                marker in error_text for marker in ["sqlalchemy", "asyncpg", "ConnectionRefused", "OperationalError"]
            )

            if is_internal_error:
                logger.error("CRITICAL SYSTEM ERROR in tool '%s': %s", tool_name, error_text, exc_info=True)
                result_str = "Error: Internal System Error. Please contact administrator."
            else:
                logger.warning("Tool execution error (%s): %s", tool_name, error_text)
                result_str = f"Error execution tool: {error_text}"

            outcome = ToolExecutionOutcome(
                tool_name=tool_name,
                worker=worker,
                status="error",
                raw_text=result_str,
                structured_data=None,
                exception_text=error_text,
                latency_ms=0,
                fingerprint=fingerprint,
                metadata=metadata,
            )

        classification = ResultClassifier.classify(outcome)
        return ToolExecutionPatch(
            message=ToolMessage(content=outcome["raw_text"], name=tool_name, tool_call_id=tool_call_id),
            outcome=outcome,
            classification=classification,
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
