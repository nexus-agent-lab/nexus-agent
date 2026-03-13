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
    trace_logger.log_wire_event(
        "reviewer_worker.prepare",
        trace_id=str(state.get("trace_id", "")),
        summary="Prepared reviewer worker context.",
        details={
            "selected_worker": "reviewer_worker",
            "last_classification": classification.get("category"),
            "next_action": classification.get("suggested_next_action"),
        },
    )

    return {
        "selected_worker": "reviewer_worker",
        "verification_status": "pending" if classification else None,
    }
