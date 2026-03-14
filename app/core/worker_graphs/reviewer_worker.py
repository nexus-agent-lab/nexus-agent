from __future__ import annotations

from app.core.state import AgentState
from app.core.trace_logger import trace_logger


async def run_reviewer_worker_step(state: AgentState) -> dict:
    """
    Minimal reviewer skeleton for future graph-level verification.

    For now, it only exposes the verification-facing summary that later worker
    subgraphs can feed into more formal pass/fail logic.
    """
    classification = state.get("last_classification") or {}
    outcome = state.get("last_outcome") or {}
    metadata = outcome.get("metadata") or {}
    execution_mode = state.get("execution_mode")
    next_execution_hint = state.get("next_execution_hint")
    next_action = classification.get("suggested_next_action")
    requires_verification = bool(metadata.get("requires_verification"))
    risk_level = metadata.get("risk_level")
    side_effect = bool(metadata.get("side_effect"))

    verification_status = None
    if classification.get("category") == "verification_failed":
        verification_status = "failed"
    elif next_execution_hint == "act":
        verification_status = "pending"
    elif next_action == "verify" or execution_mode == "skill_verify":
        verification_status = "required"
    elif classification.get("category") == "success" and (requires_verification or side_effect or risk_level == "high"):
        verification_status = "required"
    elif classification.get("requires_handoff") or next_action == "handoff":
        verification_status = "failed"
    elif classification.get("category") == "success" and next_action == "complete":
        verification_status = "passed"
    elif classification:
        verification_status = "pending"

    trace_logger.log_wire_event(
        "reviewer_worker.prepare",
        trace_id=str(state.get("trace_id", "")),
        summary="Prepared reviewer worker context.",
        details={
            "selected_worker": "reviewer_worker",
            "last_classification": classification.get("category"),
            "next_action": next_action,
            "next_execution_hint": next_execution_hint,
            "execution_mode": execution_mode,
            "requires_verification": requires_verification,
            "risk_level": risk_level,
            "side_effect": side_effect,
            "verification_status": verification_status,
        },
    )

    return {
        "selected_worker": "reviewer_worker",
        "verification_status": verification_status,
    }
