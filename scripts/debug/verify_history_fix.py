import asyncio
import os
import uuid

from app.core.mq import ChannelType, MessageType, UnifiedMessage

# Mock environment
os.environ["LLM_API_KEY"] = "sk-dummy"
os.environ["LLM_BASE_URL"] = "http://localhost:11434/v1"

# Import Worker to test _process_message logic
from app.core.worker import AgentWorker


async def test_history_deduplication():
    print("--- Testing History Deduplication ---")

    # Mock SessionManager
    from unittest.mock import AsyncMock, MagicMock, patch

    # Create a mock user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "test_user"
    mock_user.role = "user"

    # Create mock history
    mock_history = [
        MagicMock(type="human", content="Hello", tool_call_id=None, tool_name=None),
        MagicMock(type="ai", content="Hi there", tool_call_id=None, tool_name=None),
    ]

    # Mock Agent Graph
    mock_graph = AsyncMock()

    # Mock astream_events to yield nothing or dummy
    async def mock_stream(*args, **kwargs):
        yield {"event": "final_answer", "data": "Done"}

    # Patch dependencies
    # Note: SessionManager is imported inside _process_message, so we patch where it is defined
    with (
        patch("app.core.session.SessionManager") as MockSessionManager,
        patch("app.core.worker.AgentWorker._resolve_user", new_callable=AsyncMock) as mock_resolve_user,
        patch("app.core.worker.MQService", new_callable=AsyncMock),
        patch("app.core.agent.stream_agent_events", side_effect=mock_stream) as mock_stream_events,
    ):
        # Setup mocks
        mock_resolve_user.return_value = mock_user

        mock_session = MagicMock()
        mock_session.id = 123
        MockSessionManager.get_or_create_session = AsyncMock(return_value=mock_session)
        MockSessionManager.get_history = AsyncMock(return_value=mock_history)

        AgentWorker.set_agent_graph(mock_graph)

        # Create a test message
        msg = UnifiedMessage(
            id=str(uuid.uuid4()),
            channel=ChannelType.TELEGRAM,
            channel_id="12345",
            content="What time is it?",
            msg_type=MessageType.TEXT,
        )

        # Run processing
        await AgentWorker._process_message(msg)

        # VERIFICATION
        # Check what was passed to stream_agent_events
        call_args = mock_stream_events.call_args
        if call_args:
            graph_arg, initial_state_arg = call_args[0]
            messages = initial_state_arg["messages"]

            print(f"Total Messages passed to Graph: {len(messages)}")
            for i, m in enumerate(messages):
                print(f"[{i}] {type(m).__name__}: {m.content}")

            # Expecting: [Human(Hello), AI(Hi there), Human(What time is it?)]
            # Count = 3
            assert len(messages) == 3
            assert messages[0].content == "Hello"
            assert messages[1].content == "Hi there"
            assert messages[2].content == "What time is it?"
            assert initial_state_arg["session_id"] == 123

            print("✅ History correctly prepended ONCE.")
        else:
            print("❌ stream_agent_events was not called.")


if __name__ == "__main__":
    asyncio.run(test_history_deduplication())
