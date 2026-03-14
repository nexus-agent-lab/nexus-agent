import pytest

from app.core.worker_graphs.reviewer_worker import run_reviewer_worker_step


@pytest.mark.asyncio
async def test_reviewer_worker_marks_verify_action_as_required():
    result = await run_reviewer_worker_step(
        {
            "last_classification": {"category": "success", "suggested_next_action": "verify"},
            "execution_mode": "skill_verify",
        }
    )

    assert result["selected_worker"] == "reviewer_worker"
    assert result["verification_status"] == "required"


@pytest.mark.asyncio
async def test_reviewer_worker_marks_complete_success_as_passed():
    result = await run_reviewer_worker_step(
        {
            "last_classification": {"category": "success", "suggested_next_action": "complete"},
            "execution_mode": "skill_read",
        }
    )

    assert result["verification_status"] == "passed"


@pytest.mark.asyncio
async def test_reviewer_worker_marks_handoff_as_failed():
    result = await run_reviewer_worker_step(
        {
            "last_classification": {
                "category": "non_retryable_runtime_error",
                "suggested_next_action": "handoff",
                "requires_handoff": True,
            },
            "execution_mode": "skill_act",
        }
    )

    assert result["verification_status"] == "failed"


@pytest.mark.asyncio
async def test_reviewer_worker_marks_verification_failed_as_failed():
    result = await run_reviewer_worker_step(
        {
            "last_classification": {
                "category": "verification_failed",
                "suggested_next_action": "ask_user",
                "requires_handoff": False,
            },
            "execution_mode": "skill_verify",
        }
    )

    assert result["verification_status"] == "failed"
