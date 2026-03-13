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
    execution_mode = state.get("execution_mode")
    next_action = classification.get("suggested_next_action")

    verification_status = None
    if next_action == "verify" or execution_mode == "skill_verify":
        verification_status = "required"
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
            "execution_mode": execution_mode,
            "verification_status": verification_status,
        },
    )

    return {
        "selected_worker": "reviewer_worker",
        "verification_status": verification_status,
    }
