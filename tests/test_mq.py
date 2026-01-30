from unittest.mock import AsyncMock

import pytest

from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage


@pytest.mark.asyncio
async def test_mq_operation(mocker):
    """Test pushing and popping from MQ with a mocked Redis."""
    # 1. Mock Redis
    mock_redis = AsyncMock()
    mocker.patch("app.core.mq.redis.from_url", return_value=mock_redis)

    # Reset internal redis reference to ensure our mock is used
    MQService._redis_instances = {}

    # 2. Create Message
    msg = UnifiedMessage(
        channel=ChannelType.TELEGRAM, channel_id="12345", content="Test Message", msg_type=MessageType.TEXT
    )

    # 3. Test Push Inbox
    await MQService.push_inbox(msg)
    mock_redis.lpush.assert_called_once()

    # 4. Test Pop Inbox
    mock_redis.rpop.return_value = msg.model_dump_json()
    popped = await MQService.pop_inbox()

    assert popped.id == msg.id
    assert popped.content == msg.content
    assert popped.channel == ChannelType.TELEGRAM
    mock_redis.rpop.assert_called_once_with(MQService.INBOX_KEY)


@pytest.mark.asyncio
async def test_queue_empty(mocker):
    """Test popping from an empty queue."""
    mock_redis = AsyncMock()
    mocker.patch("app.core.mq.redis.from_url", return_value=mock_redis)
    MQService._redis_instances = {}

    mock_redis.rpop.return_value = None
    popped = await MQService.pop_inbox()
    assert popped is None
