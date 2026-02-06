from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.product import ProductSuggestion
from app.models.user import User
from app.tools.suggestion_tools import submit_suggestion, update_suggestion_status


@pytest.mark.asyncio
async def test_submit_suggestion():
    # Mock user
    user = User(id=1, username="test_user", role="user")

    # Mock DB session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Patch BOTH locations where AsyncSessionLocal is usage
    with (
        patch("app.core.db.AsyncSessionLocal", return_value=mock_session),
        patch("app.tools.suggestion_tools.AsyncSessionLocal", return_value=mock_session),
    ):
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Access the underlying async function
        result = await submit_suggestion.coroutine(content="Fix the bug", category="bug", user_id=1, user_object=user)

        assert "submitted successfully" in result
        mock_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_submit_suggestion_no_user():
    # Calling the coroutine directly
    result = await submit_suggestion.coroutine(content="Fix the bug", category="bug")
    assert "Error: User context required" in result


@pytest.mark.asyncio
async def test_update_status_invalid():
    user = User(id=99, username="admin", role="admin")
    mock_session = AsyncMock()

    with (
        patch("app.core.db.AsyncSessionLocal", return_value=mock_session),
        patch("app.tools.suggestion_tools.AsyncSessionLocal", return_value=mock_session),
    ):
        mock_session.__aenter__.return_value = mock_session
        result = await update_suggestion_status.coroutine(
            suggestion_id=1, status="invalid_status", user_id=99, user_object=user
        )
        assert "Error: Invalid status" in result


@pytest.mark.asyncio
async def test_update_status_success():
    user = User(id=99, username="admin", role="admin")
    mock_suggestion = ProductSuggestion(id=1, status="pending")

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_suggestion)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    with (
        patch("app.core.db.AsyncSessionLocal", return_value=mock_session),
        patch("app.tools.suggestion_tools.AsyncSessionLocal", return_value=mock_session),
    ):
        mock_session.__aenter__.return_value = mock_session

        result = await update_suggestion_status.coroutine(
            suggestion_id=1, status="approved", user_id=99, user_object=user
        )

        assert "updated to 'approved'" in result
