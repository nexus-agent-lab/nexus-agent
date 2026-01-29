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
    API = "api"


class MessageType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    SYSTEM = "system"  # For internal notifications
    UPDATE = "update"  # For modifying existing messages


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

    _redis: Optional[redis.Redis] = None

    INBOX_KEY = "mq:inbox"
    OUTBOX_KEY = "mq:outbox"

    @classmethod
    async def get_redis(cls) -> redis.Redis:
        if cls._redis is None:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            cls._redis = redis.from_url(redis_url, decode_responses=True)
        return cls._redis

    @classmethod
    async def close(cls):
        if cls._redis:
            await cls._redis.close()
            cls._redis = None

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
