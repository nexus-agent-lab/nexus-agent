import asyncio
import logging
import os
import time
import uuid
from enum import Enum
from typing import Any, Dict, Optional

import redis.asyncio as redis
from pydantic import BaseModel, Field

logger = logging.getLogger("nexus.mq")

# ==========================================
# Schema Definitions
# ==========================================


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"  # Reserved
    HTTP = "http"  # For direct API calls
    API = "api"


class MessageType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    SYSTEM = "system"  # For internal notifications
    UPDATE = "update"  # For modifying existing messages
    ACTION = "action"  # For chat actions like 'typing'


class UnifiedMessage(BaseModel):
    """
    Standardized Message Envelope for all communication channels.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel: ChannelType
    channel_id: str  # Chat ID, User ID, or Group ID
    user_id: Optional[str] = None  # Internal Nexus User ID if resolved
    content: str
    msg_type: MessageType = MessageType.TEXT
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


# ==========================================
# Message Queue Service
# ==========================================


class MQService:
    """
    Handles persistence of messages using Redis Lists.
    - Inbox: Incoming messages from external platforms (Producer: Poller, Consumer: Agent)
    - Outbox: Outgoing messages from Agent (Producer: Agent, Consumer: Dispatcher)
    """

    _redis_instances: Dict[int, redis.Redis] = {}

    INBOX_KEY = "mq:inbox"
    OUTBOX_KEY = "mq:outbox"
    DLQ_KEY = "mq:dlq"

    @classmethod
    async def get_redis(cls) -> redis.Redis:
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
        except RuntimeError:
            # Should not happen in async context, but fallback
            loop_id = 0

        if loop_id not in cls._redis_instances:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            # Create a new client for this loop
            client = redis.from_url(redis_url, decode_responses=True)
            cls._redis_instances[loop_id] = client
            logger.debug(f"Created new Redis client for loop {loop_id}")

        return cls._redis_instances[loop_id]

    @classmethod
    async def close(cls):
        # Close all instances
        for loop_id, client in list(cls._redis_instances.items()):
            try:
                await client.close()
            except Exception:
                pass
            del cls._redis_instances[loop_id]

    @classmethod
    async def push_inbox(cls, message: UnifiedMessage):
        """Push a message to the Inbox (Called by Interface Adapters)."""
        r = await cls.get_redis()
        try:
            # LPUSH: Add to head
            await r.lpush(cls.INBOX_KEY, message.model_dump_json())
            logger.debug(f"MQ INBOX Push: {message.id} ({message.channel})")
        except Exception as e:
            logger.error(f"Failed to push to INBOX: {e}")
            raise

    @classmethod
    async def pop_inbox(cls) -> Optional[UnifiedMessage]:
        """Pop a message from the Inbox (Called by Agent Worker)."""
        r = await cls.get_redis()
        try:
            # RPOP: Remove from tail (FIFO)
            data = await r.rpop(cls.INBOX_KEY)
            if data:
                return UnifiedMessage.model_validate_json(data)
        except Exception as e:
            logger.error(f"Failed to pop from INBOX: {e}")
        return None

    @classmethod
    async def push_outbox(cls, message: UnifiedMessage):
        """Push a message to the Outbox (Called by Agent)."""
        r = await cls.get_redis()
        try:
            await r.lpush(cls.OUTBOX_KEY, message.model_dump_json())
            logger.debug(f"MQ OUTBOX Push: {message.id} ({message.channel})")
        except Exception as e:
            logger.error(f"Failed to push to OUTBOX: {e}")
            raise

    @classmethod
    async def push_dlq(cls, message: UnifiedMessage, error_msg: str = ""):
        r = await cls.get_redis()
        try:
            message.meta["dlq_error"] = error_msg
            message.meta["dlq_timestamp"] = time.time()
            await r.lpush(cls.DLQ_KEY, message.model_dump_json())
            logger.warning(f"Message {message.id} sent to DLQ ({message.channel}). Error: {error_msg}")
        except Exception as e:
            logger.error(f"Failed to push to DLQ: {e}")

    @classmethod
    async def pop_outbox(cls) -> Optional[UnifiedMessage]:
        """Pop a message from the Outbox (Called by Dispatcher)."""
        r = await cls.get_redis()
        try:
            data = await r.rpop(cls.OUTBOX_KEY)
            if data:
                return UnifiedMessage.model_validate_json(data)
        except Exception as e:
            logger.error(f"Failed to pop from OUTBOX: {e}")
        return None
