from __future__ import annotations

from typing import Literal, TypedDict

from app.core.tool_executor import ToolExecutionOutcome


class ResultClassification(TypedDict, total=False):
    """Graph-facing result classification used for deterministic branching."""

    category: Literal[
        "success",
        "invalid_input",
        "wrong_tool_or_domain",
        "permission_denied",
        "retryable_upstream_error",
        "retryable_runtime_error",
        "non_retryable_runtime_error",
        "unsafe_state",
        "verification_failed",
    ]
    retryable: bool
    should_switch_worker: bool
    requires_handoff: bool
    user_facing_summary: str
    debug_summary: str
    suggested_next_action: Literal[
        "retry_same_worker",
        "switch_worker",
        "run_discovery",
        "ask_user",
        "handoff",
        "verify",
        "complete",
    ]


def _contains(text: str, *needles: str) -> bool:
    lowered = (text or "").lower()
    return any(needle in lowered for needle in needles)


class ResultClassifier:
    """Deterministic first-pass result classifier for graph branching."""

    @staticmethod
    def classify(outcome: ToolExecutionOutcome) -> ResultClassification:
        metadata = outcome.get("metadata", {})
        raw_text = outcome.get("raw_text", "")
        exception_text = outcome.get("exception_text", "")
        debug_summary = raw_text or exception_text or "Unknown tool result"

        if outcome.get("status") == "success":
            if _contains(raw_text, "permission denied", "restricted for user"):
                return ResultClassification(
                    category="permission_denied",
                    retryable=False,
                    should_switch_worker=False,
                    requires_handoff=False,
                    user_facing_summary="Permission denied.",
                    debug_summary=debug_summary,
                    suggested_next_action="ask_user",
                )

            if _contains(raw_text, "unsafe", "dangerous state", "interlock"):
                return ResultClassification(
                    category="unsafe_state",
                    retryable=False,
                    should_switch_worker=False,
                    requires_handoff=True,
                    user_facing_summary="The system reported an unsafe state.",
                    debug_summary=debug_summary,
                    suggested_next_action="handoff",
                )

            if _contains(raw_text, "entity not found", "service not found", "not found"):
                return ResultClassification(
                    category="invalid_input",
                    retryable=False,
                    should_switch_worker=False,
                    requires_handoff=False,
                    user_facing_summary="The requested resource could not be found.",
                    debug_summary=debug_summary,
                    suggested_next_action="run_discovery",
                )

            if metadata.get("requires_verification"):
                return ResultClassification(
                    category="success",
                    retryable=False,
                    should_switch_worker=False,
                    requires_handoff=False,
                    user_facing_summary="Execution finished and requires verification.",
                    debug_summary=debug_summary,
                    suggested_next_action="verify",
                )

            return ResultClassification(
                category="success",
                retryable=False,
                should_switch_worker=False,
                requires_handoff=False,
                user_facing_summary="Execution completed successfully.",
                debug_summary=debug_summary,
                suggested_next_action="complete",
            )

        if _contains(exception_text, "permission denied", "restricted for user"):
            return ResultClassification(
                category="permission_denied",
                retryable=False,
                should_switch_worker=False,
                requires_handoff=False,
                user_facing_summary="Permission denied.",
                debug_summary=debug_summary,
                suggested_next_action="ask_user",
            )

        if _contains(exception_text, "timeout", "connection refused", "temporarily unavailable", "503"):
            return ResultClassification(
                category="retryable_upstream_error",
                retryable=True,
                should_switch_worker=False,
                requires_handoff=False,
                user_facing_summary="The upstream service is temporarily unavailable.",
                debug_summary=debug_summary,
                suggested_next_action="retry_same_worker",
            )

        if _contains(exception_text, "syntaxerror", "nameerror", "typeerror", "valueerror", "importerror"):
            return ResultClassification(
                category="retryable_runtime_error",
                retryable=True,
                should_switch_worker=False,
                requires_handoff=False,
                user_facing_summary="Execution failed with a repairable runtime error.",
                debug_summary=debug_summary,
                suggested_next_action="retry_same_worker",
            )

        if _contains(exception_text, "tool not found", "wrong tool", "no such tool"):
            return ResultClassification(
                category="wrong_tool_or_domain",
                retryable=False,
                should_switch_worker=True,
                requires_handoff=False,
                user_facing_summary="The selected tool does not match the task.",
                debug_summary=debug_summary,
                suggested_next_action="switch_worker",
            )

        return ResultClassification(
            category="non_retryable_runtime_error",
            retryable=False,
            should_switch_worker=False,
            requires_handoff=True,
            user_facing_summary="Execution failed and needs intervention.",
            debug_summary=debug_summary,
            suggested_next_action="handoff",
        )
