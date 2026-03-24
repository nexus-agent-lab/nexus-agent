import asyncio
import base64
import json
import logging
import os
import random
import secrets
from typing import Any

import aiohttp

from app.core.audit import record_audit_event
from app.core.dispatcher import InterfaceDispatcher
from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage

logger = logging.getLogger("nexus.wechat")

WECHAT_ENABLED = os.getenv("WECHAT_ENABLED", "false").lower() == "true"
WECHAT_BASE_URL = os.getenv("WECHAT_BASE_URL", "https://ilinkai.weixin.qq.com").rstrip("/")
WECHAT_CHANNEL_VERSION = os.getenv("WECHAT_CHANNEL_VERSION", "1.0.2")
WECHAT_BOT_TOKEN = os.getenv("WECHAT_BOT_TOKEN", "")
WECHAT_BOT_QRCODE = os.getenv("WECHAT_BOT_QRCODE", "")
WECHAT_POLL_INTERVAL_SECONDS = float(os.getenv("WECHAT_POLL_INTERVAL_SECONDS", "1.0"))

_wechat_session: aiohttp.ClientSession | None = None
_wechat_bot_token: str | None = WECHAT_BOT_TOKEN or None
_wechat_get_updates_buf = ""
_wechat_context_tokens: dict[str, str] = {}
_wechat_typing_tickets: dict[str, str] = {}
_wechat_login_recorded = False


def _make_headers(token: str | None = None) -> dict[str, str]:
    uin = str(random.randint(0, 0xFFFFFFFF))
    headers = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": base64.b64encode(uin.encode()).decode(),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _extract_wechat_text(msg: dict[str, Any]) -> str:
    if msg.get("message_type") != 1:
        return ""

    for item in msg.get("item_list") or []:
        if item.get("type") == 1:
            return item.get("text_item", {}).get("text", "")
    return ""


def _build_sendmessage_payload(*, to_user_id: str, context_token: str, text: str) -> dict[str, Any]:
    client_id = f"openclaw-weixin-{secrets.token_hex(4)}"
    return {
        "msg": {
            "from_user_id": "",
            "to_user_id": to_user_id,
            "client_id": client_id,
            "message_type": 2,
            "message_state": 2,
            "context_token": context_token,
            "item_list": [{"type": 1, "text_item": {"text": text}}],
        },
        "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
    }


async def _api_get_json(
    session: aiohttp.ClientSession, path: str, *, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    url = f"{WECHAT_BASE_URL}/{path.lstrip('/')}"
    async with session.get(url, params=params, headers=_make_headers()) as response:
        try:
            return await response.json(content_type=None)
        except Exception:
            text = await response.text()
            logger.warning("WeChat GET %s returned non-JSON response: %s", path, text[:200])
            return {}


async def _api_post_json(
    session: aiohttp.ClientSession,
    path: str,
    body: dict[str, Any],
    *,
    token: str | None = None,
) -> dict[str, Any]:
    url = f"{WECHAT_BASE_URL}/{path.lstrip('/')}"
    async with session.post(url, json=body, headers=_make_headers(token)) as response:
        text = await response.text()
        try:
            return json.loads(text)
        except Exception:
            logger.warning("WeChat POST %s returned non-JSON response: %s", path, text[:200])
            return {}


async def _get_session() -> aiohttp.ClientSession:
    global _wechat_session
    if _wechat_session is None or _wechat_session.closed:
        _wechat_session = aiohttp.ClientSession()
    return _wechat_session


async def _ensure_wechat_login() -> str | None:
    global _wechat_bot_token, _wechat_login_recorded

    if _wechat_bot_token:
        if not _wechat_login_recorded:
            await record_audit_event(
                action="channel.wechat.login_completed",
                user_id=None,
                tool_name="wechat",
                tool_args={"mode": "configured_token"},
            )
            _wechat_login_recorded = True
        return _wechat_bot_token

    if not WECHAT_ENABLED:
        return None

    session = await _get_session()
    qrcode = WECHAT_BOT_QRCODE
    if not qrcode:
        await record_audit_event(
            action="channel.wechat.login_started",
            user_id=None,
            tool_name="wechat",
            tool_args={"mode": "qr_login"},
        )
        qrcode_payload = await _api_get_json(session, "ilink/bot/get_bot_qrcode", params={"bot_type": 3})
        qrcode = qrcode_payload.get("qrcode", "")
        qrcode_url = qrcode_payload.get("qrcode_img_content") or qrcode_payload.get("qrcode_url")
        logger.info("WeChat QR login started. qrcode=%s", qrcode)
        if qrcode_url:
            logger.info("Open this WeChat QR URL on your phone to authorize Nexus: %s", qrcode_url)

    if not qrcode:
        logger.error("WeChat login could not start because no qrcode was returned.")
        return None

    logger.info("Waiting for WeChat QR confirmation...")
    while True:
        status_payload = await _api_get_json(session, "ilink/bot/get_qrcode_status", params={"qrcode": qrcode})
        if status_payload.get("status") == "confirmed":
            _wechat_bot_token = status_payload.get("bot_token")
            if _wechat_bot_token:
                await record_audit_event(
                    action="channel.wechat.login_completed",
                    user_id=None,
                    tool_name="wechat",
                    tool_args={"mode": "qr_login"},
                )
                _wechat_login_recorded = True
                logger.info("WeChat login completed successfully.")
                return _wechat_bot_token
        await asyncio.sleep(WECHAT_POLL_INTERVAL_SECONDS)


async def _ensure_typing_ticket(
    session: aiohttp.ClientSession,
    *,
    bot_token: str,
    user_id: str,
    context_token: str,
) -> str | None:
    ticket = _wechat_typing_tickets.get(user_id)
    if ticket:
        return ticket

    config_payload = await _api_post_json(
        session,
        "ilink/bot/getconfig",
        {
            "ilink_user_id": user_id,
            "context_token": context_token,
            "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
        },
        token=bot_token,
    )
    ticket = config_payload.get("typing_ticket")
    if ticket:
        _wechat_typing_tickets[user_id] = ticket
    return ticket


async def _send_typing_status(
    session: aiohttp.ClientSession,
    *,
    bot_token: str,
    user_id: str,
    context_token: str,
    status: int,
) -> None:
    ticket = await _ensure_typing_ticket(session, bot_token=bot_token, user_id=user_id, context_token=context_token)
    if not ticket:
        return

    await _api_post_json(
        session,
        "ilink/bot/sendtyping",
        {"ilink_user_id": user_id, "typing_ticket": ticket, "status": status},
        token=bot_token,
    )


async def send_wechat_message(msg: UnifiedMessage):
    bot_token = await _ensure_wechat_login()
    if not bot_token:
        logger.warning("WeChat bot token is unavailable, cannot send outbound message.")
        return

    session = await _get_session()
    target_user_id = msg.channel_id
    context_token = _wechat_context_tokens.get(target_user_id)

    if msg.msg_type == MessageType.ACTION:
        if msg.content == "typing" and context_token:
            await _send_typing_status(
                session,
                bot_token=bot_token,
                user_id=target_user_id,
                context_token=context_token,
                status=1,
            )
        return

    if not context_token:
        logger.warning("No WeChat context token cached for %s; skipping outbound message.", target_user_id)
        return

    await _send_typing_status(
        session,
        bot_token=bot_token,
        user_id=target_user_id,
        context_token=context_token,
        status=1,
    )
    payload = _build_sendmessage_payload(
        to_user_id=target_user_id,
        context_token=context_token,
        text=msg.content,
    )
    await _api_post_json(session, "ilink/bot/sendmessage", payload, token=bot_token)
    await _send_typing_status(
        session,
        bot_token=bot_token,
        user_id=target_user_id,
        context_token=context_token,
        status=2,
    )
    await record_audit_event(
        action="channel.wechat.message_sent",
        user_id=None,
        tool_name="wechat",
        tool_args={"to_user_id": target_user_id, "message_type": msg.msg_type.value},
    )


async def _handle_inbound_message(raw_message: dict[str, Any]):
    text = _extract_wechat_text(raw_message)
    if not text:
        return

    from_user_id = str(raw_message.get("from_user_id", ""))
    context_token = raw_message.get("context_token", "")
    if not from_user_id or not context_token:
        logger.warning("Skipping malformed WeChat message: missing from_user_id or context_token.")
        return

    _wechat_context_tokens[from_user_id] = context_token
    unified = UnifiedMessage(
        channel=ChannelType.WECHAT,
        channel_id=from_user_id,
        content=text,
        msg_type=MessageType.TEXT,
        meta={
            "username": from_user_id,
            "wechat_username": from_user_id,
            "wechat_from_user_id": from_user_id,
            "wechat_context_token": context_token,
            "wechat_to_user_id": raw_message.get("to_user_id", ""),
            "wechat_message_type": raw_message.get("message_type"),
        },
    )
    await MQService.push_inbox(unified)
    await record_audit_event(
        action="channel.wechat.message_received",
        user_id=None,
        tool_name="wechat",
        tool_args={"from_user_id": from_user_id, "message_type": raw_message.get("message_type")},
    )


async def run_wechat_bot():
    if not WECHAT_ENABLED:
        logger.info("WECHAT_ENABLED is false. WeChat interface disabled.")
        return

    bot_token = await _ensure_wechat_login()
    if not bot_token:
        logger.warning("WeChat login did not complete. Adapter will not start polling.")
        return

    InterfaceDispatcher.register_handler(ChannelType.WECHAT, send_wechat_message)
    session = await _get_session()
    logger.info("Starting WeChat polling loop...")

    global _wechat_get_updates_buf
    while True:
        try:
            result = await _api_post_json(
                session,
                "ilink/bot/getupdates",
                {
                    "get_updates_buf": _wechat_get_updates_buf,
                    "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
                },
                token=bot_token,
            )
            _wechat_get_updates_buf = result.get("get_updates_buf") or _wechat_get_updates_buf

            for raw_message in result.get("msgs") or []:
                await _handle_inbound_message(raw_message)

            await asyncio.sleep(WECHAT_POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("WeChat polling loop error: %s", exc, exc_info=True)
            await asyncio.sleep(max(WECHAT_POLL_INTERVAL_SECONDS, 1.0))
