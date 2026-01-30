import asyncio
import json
import logging
import os
from typing import Any

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    UpdateMessageRequest,
    UpdateMessageRequestBody,
)
from lark_oapi.ws import Client as WSClient

from app.core.dispatcher import InterfaceDispatcher
from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage

logger = logging.getLogger("nexus.feishu")

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
# Optional: Verification Token mostly for verification URL check if using Webhook,
# but WS doesn't strictly need it exposed, though good for security.

_feishu_client = None
_ws_client = None

# ==========================================
# 1. Outbound Handler (Consumer)
# ==========================================


async def send_feishu_message(msg: UnifiedMessage):
    """
    Handler registered with Dispatcher to send messages via Feishu.
    """
    if not _feishu_client:
        logger.warning("Feishu Client not initialized, cannot send message.")
        return

    chat_id = msg.channel_id
    text = msg.content
    target_msg_id = msg.meta.get("target_message_id")

    # Feishu uses 'open_id', 'chat_id', 'user_id', 'email' etc.
    # We assume 'channel_id' is a valid receive_id (e.g. open_id or chat_id).
    # Defaulting to 'open_id' usually safer for direct messages, but let's try auto-detect or default to open_id.
    # Actually, for P2P it's open_id. For groups it's chat_id.
    # We'll use 'receive_id_type' from meta if provided, else guess.
    receive_id_type = msg.meta.get("feishu_receive_id_type", "open_id")

    try:
        if msg.msg_type == MessageType.UPDATE and target_msg_id:
            # Edit existing message (Message Card only?)
            # Standard Text messages in Feishu might NOT be editable via API easily unless sent as cards?
            # Actually, Feishu allows editing text messages sent by the bot.
            # API: PUT /open-apis/im/v1/messages/:message_id

            # Construct edit request
            content = json.dumps({"text": text})
            req = (
                UpdateMessageRequest.builder()
                .message_id(target_msg_id)
                .request_body(UpdateMessageRequestBody.builder().content(content).msg_type("text").build())
                .build()
            )

            resp = await _feishu_client.im.v1.message.aupdate(req)
            if not resp.success():
                logger.error(f"Feishu Edit Failed: {resp.code} - {resp.msg}")

        else:
            # Send New Message
            # For simplicity, we send plain text.
            # Could upgrade to Post/RichText later.
            content = json.dumps({"text": text})

            # If msg.meta has target_message_id, we might want to edit it, but assuming new message flow logic
            # handles edits in the IF block above.

            req = (
                CreateMessageRequest.builder()
                .receive_id_type(receive_id_type)
                .request_body(
                    CreateMessageRequestBody.builder().receive_id(chat_id).msg_type("text").content(content).build()
                )
                .build()
            )

            resp = await _feishu_client.im.v1.message.acreate(req)

            if not resp.success():
                logger.error(f"Feishu Send Failed: {resp.code} - {resp.msg}")

    except Exception as e:
        logger.error(f"Failed to send Feishu message to {chat_id}: {e}")


# ==========================================
# 2. Inbound Handler (WebSocket)
# ==========================================


def do_process_message(data: Any) -> None:
    """
    Sync wrapper to bridge Lark's sync callback to our async MQ.
    Ideally we want an async callback, but let's check what Lark WS client supports.
    Lark WS client runs in a thread loop. We can use asyncio.run or run_coroutine_threadsafe.
    """
    msg_content = json.loads(data.event.message.content)
    msg_content.get("text", "")

    # Run async process in the background
    # Since we are in a separate thread (likely), we should find the main event loop
    # or just launch a new task if possible.

    # Note: Lark WS Client call back is standard threading.
    # We will use a helper to fire-and-forget to MQ.
    asyncio.run(_push_to_mq(data.event))


async def _push_to_mq(event: Any):
    content_dict = json.loads(event.message.content)
    text = content_dict.get("text", "")

    # 1. Send Thinking Status
    # We can't easily return a handle to edit later unless we send a message NOW.
    # Feishu doesn't have "typing" status API exposed easily for bots?
    # We'll skip the immediate "Thinking" message for now to avoid spam,
    # OR we implement it identically to Telegram.

    # Let's create the message
    msg = UnifiedMessage(
        channel=ChannelType.FEISHU,
        channel_id=event.sender.sender_id.open_id,  # Default reply to Sender (P2P)
        content=text,
        msg_type=MessageType.TEXT,
        meta={
            "feishu_chat_id": event.message.chat_id,
            "feishu_message_id": event.message.message_id,
            "feishu_sender_id": event.sender.sender_id.open_id,
            "feishu_receive_id_type": "open_id",  # Default response type
        },
    )

    # If group chat, channel_id should be chat_id
    if event.message.chat_type == "group":
        msg.channel_id = event.message.chat_id
        msg.meta["feishu_receive_id_type"] = "chat_id"

    await MQService.push_inbox(msg)


# ==========================================
# 3. Lifecycle
# ==========================================


async def run_feishu_bot():
    """Initializer for the Feishu Interface"""
    global _feishu_client, _ws_client

    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        logger.warning("FEISHU_APP_ID or FEISHU_APP_SECRET not set. Feishu Interface disabled.")
        return

    logger.info(f"Initializing Feishu Bot (App ID: {FEISHU_APP_ID})...")

    # 1. Initialize API Client (for outbound)
    _feishu_client = (
        lark.Client.builder().app_id(FEISHU_APP_ID).app_secret(FEISHU_APP_SECRET).log_level(lark.LogLevel.INFO).build()
    )

    # 2. Register Outbound Handler
    InterfaceDispatcher.register_handler(ChannelType.FEISHU, send_feishu_message)

    # 3. Initialize WebSocket Client (for inbound)
    # Using the standard WS client to listen for events

    # Handler for P2P/Group Text Messages
    # Note: 'im.v1.message.receive_v1' is the event key

    event_handler = (
        lark.EventDispatcherHandler.builder("", "").register_p2_message_receive_v1(do_process_message).build()
    )

    # BUT wait, the WS Client in Lark Python SDK (v1.4+) handles this differently.
    # We need to construct the WS client.

    _ws_client = WSClient(
        app_id=FEISHU_APP_ID, app_secret=FEISHU_APP_SECRET, event_handler=event_handler, log_level=lark.LogLevel.INFO
    )

    # Start WS Client (This blocks? No, start() is usually non-blocking or runs in thread)
    # Documentation says: ws_client.start() starts the loop.
    # We should run this in a way that doesn't block our main loop.
    # The WS Client likely uses threading.

    logger.info("Starting Feishu WebSocket Client...")
    _ws_client.start()

    # Keep reference to prevent GC?
    # It runs in daemon threads usually.
