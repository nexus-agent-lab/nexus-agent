import pytest
from langchain_core.messages import AIMessage

from app.core.session import SessionManager


@pytest.mark.asyncio
async def test_compact_for_token_budget_compacts_when_history_is_long(test_db, mocker):
    class DummyLLM:
        async def ainvoke(self, prompt):
            return AIMessage(content="summary")

    mocker.patch("app.core.session.get_llm_client", return_value=DummyLLM())

    session = await SessionManager.get_or_create_session(user_id=1)
    for idx in range(18):
        role = "user" if idx % 2 == 0 else "assistant"
        kind = "human" if role == "user" else "ai"
        await SessionManager.save_message(session.id, role, kind, f"message {idx}")

    compacted = await SessionManager.compact_for_token_budget(
        session.id,
        estimated_input_tokens=180000,
        target_tokens=100000,
    )

    assert compacted is True
    summary, recent = await SessionManager.get_history_with_summary(session.id, limit=15)
    assert "summary" in summary
    assert len(recent) <= 15
