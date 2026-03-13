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
async def test_reviewer_worker_marks_non_verify_classification_pending():
    result = await run_reviewer_worker_step(
        {
            "last_classification": {"category": "success", "suggested_next_action": "complete"},
            "execution_mode": "skill_read",
        }
    )

    assert result["verification_status"] == "pending"
