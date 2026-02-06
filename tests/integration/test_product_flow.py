import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.product import ProductSuggestion
from app.models.user import User

# We need a fixture to clean up DB or run in transaction
# For simplicity, assuming the standard conftest handles session isolation or we clean up manually


@pytest.mark.asyncio
async def test_full_suggestion_lifecycle(test_db: AsyncSession):
    # 1. Setup Data
    user_data = User(username="integ_user", role="user", api_key="test_key_user")
    admin_data = User(username="integ_admin", role="admin", api_key="test_key_admin")

    test_db.add(user_data)
    test_db.add(admin_data)
    await test_db.commit()
    await test_db.refresh(user_data)
    await test_db.refresh(admin_data)
    user_id = user_data.id
    admin_id = admin_data.id

    # 2. User submits suggestion
    # IMPORT INSIDE FUNCTION to ensure we get the patched AsyncSessionLocal from conftest
    # Manually patch the module-level attribute to match the test DB sessionmaker
    # This is required because suggestion_tools imported AsyncSessionLocal at load time
    import app.core.db
    from app.tools import suggestion_tools

    original_tool_session = suggestion_tools.AsyncSessionLocal
    suggestion_tools.AsyncSessionLocal = app.core.db.AsyncSessionLocal

    try:
        from app.tools.suggestion_tools import submit_suggestion, update_suggestion_status

        # Submit
        res_submit = await submit_suggestion.coroutine(
            content="Integration Test Idea", category="feature", user_id=user_id, user_object=user_data
        )
        assert "submitted successfully" in res_submit

        # Verify in DB
        result = await test_db.execute(
            select(ProductSuggestion).where(ProductSuggestion.content == "Integration Test Idea")
        )
        suggestion = result.scalars().first()
        assert suggestion is not None
        assert suggestion.status == "pending"
        suggestion_id = suggestion.id

        # 3. Admin approves suggestion
        res_update = await update_suggestion_status.coroutine(
            suggestion_id=suggestion_id, status="approved", user_id=admin_id, user_object=admin_data
        )
        assert "updated to 'approved'" in res_update

        # 4. Verify Final State
        await test_db.refresh(suggestion)
        assert suggestion.status == "approved"

    finally:
        suggestion_tools.AsyncSessionLocal = original_tool_session
