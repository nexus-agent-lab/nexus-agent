import asyncio
import base64
import json
import logging
import os
import random
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import aiohttp
import redis.asyncio as redis
from sqlmodel import select

from app.core.audit import record_audit_event
from app.core.db import AsyncSessionLocal
from app.core.dispatcher import InterfaceDispatcher
from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage
from app.core.security import decrypt_secret, encrypt_secret
from app.models.secret import Secret, SecretScope

logger = logging.getLogger("nexus.wechat")

WECHAT_ENABLED = os.getenv("WECHAT_ENABLED", "true").lower() != "false"
WECHAT_BASE_URL = os.getenv("WECHAT_BASE_URL", "https://ilinkai.weixin.qq.com").rstrip("/")
WECHAT_CHANNEL_VERSION = os.getenv("WECHAT_CHANNEL_VERSION", "1.0.2")
WECHAT_POLL_INTERVAL_SECONDS = float(os.getenv("WECHAT_POLL_INTERVAL_SECONDS", "1.0"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

WECHAT_SECRET_KEY = "WECHAT_BOT_TOKEN"
WECHAT_BINDING_TTL_SECONDS = 600

_wechat_http_session: aiohttp.ClientSession | None = None
_dispatcher_registered = False
_wechat_channel_user_map: dict[str, int] = {}
_wechat_runtime_sessions: dict[str, "WeChatRuntimeSession"] = {}


@dataclass
class WeChatRuntimeSession:
    session_key: str
    owner_user_id: int | None
    bot_token: str
    base_url: str | None = None
    get_updates_buf: str = ""
    context_tokens: dict[str, str] = field(default_factory=dict)
    typing_tickets: dict[str, str] = field(default_factory=dict)
    task: asyncio.Task | None = None


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


def _mask_token(token: str | None) -> str | None:
    if not token:
        return None
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}...{token[-4:]}"


def _runtime_session_key(owner_user_id: int | None) -> str:
    return f"user:{owner_user_id}"


def _binding_session_key(session_id: str) -> str:
    return f"wechat:binding:{session_id}"


async def _get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


async def _get_http_session() -> aiohttp.ClientSession:
    global _wechat_http_session
    if _wechat_http_session is None or _wechat_http_session.closed:
        _wechat_http_session = aiohttp.ClientSession()
    return _wechat_http_session


async def _api_get_json(
    session: aiohttp.ClientSession,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    url = f"{(base_url or WECHAT_BASE_URL).rstrip('/')}/{path.lstrip('/')}"
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
    base_url: str | None = None,
) -> dict[str, Any]:
    url = f"{(base_url or WECHAT_BASE_URL).rstrip('/')}/{path.lstrip('/')}"
    async with session.post(url, json=body, headers=_make_headers(token)) as response:
        text = await response.text()
        try:
            return json.loads(text)
        except Exception:
            logger.warning("WeChat POST %s returned non-JSON response: %s", path, text[:200])
            return {}


async def _save_binding_session(session_id: str, payload: dict[str, Any]) -> None:
    redis_client = await _get_redis()
    try:
        await redis_client.setex(
            _binding_session_key(session_id),
            WECHAT_BINDING_TTL_SECONDS,
            json.dumps(payload),
        )
    finally:
        await redis_client.aclose()


async def _load_binding_session(session_id: str) -> dict[str, Any] | None:
    redis_client = await _get_redis()
    try:
        raw = await redis_client.get(_binding_session_key(session_id))
    finally:
        await redis_client.aclose()
    if not raw:
        return None
    return json.loads(raw)


async def _delete_binding_session(session_id: str) -> None:
    redis_client = await _get_redis()
    try:
        await redis_client.delete(_binding_session_key(session_id))
    finally:
        await redis_client.aclose()


async def _upsert_wechat_secret(user_id: int, bot_token: str) -> None:
    encrypted = encrypt_secret(bot_token)
    async with AsyncSessionLocal() as session:
        stmt = select(Secret).where(
            Secret.owner_id == user_id,
            Secret.key == WECHAT_SECRET_KEY,
            Secret.scope == SecretScope.user_scope,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.encrypted_value = encrypted
            session.add(existing)
        else:
            session.add(
                Secret(
                    key=WECHAT_SECRET_KEY,
                    encrypted_value=encrypted,
                    scope=SecretScope.user_scope,
                    owner_id=user_id,
                )
            )
        await session.commit()


async def _get_user_wechat_secret(user_id: int) -> str | None:
    async with AsyncSessionLocal() as session:
        stmt = select(Secret).where(
            Secret.owner_id == user_id,
            Secret.key == WECHAT_SECRET_KEY,
            Secret.scope == SecretScope.user_scope,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if not existing:
            return None
        return decrypt_secret(existing.encrypted_value)


async def _list_bound_wechat_tokens() -> list[tuple[int, str]]:
    async with AsyncSessionLocal() as session:
        stmt = select(Secret).where(
            Secret.key == WECHAT_SECRET_KEY,
            Secret.scope == SecretScope.user_scope,
            Secret.owner_id.is_not(None),
        )
        result = await session.execute(stmt)
        secrets_rows = result.scalars().all()
        return [
            (secret.owner_id, decrypt_secret(secret.encrypted_value))
            for secret in secrets_rows
            if secret.owner_id is not None
        ]


async def get_user_wechat_binding_status(user_id: int) -> dict[str, Any]:
    token = await _get_user_wechat_secret(user_id)
    runtime = _wechat_runtime_sessions.get(_runtime_session_key(user_id))
    return {
        "connected": bool(token),
        "polling_active": runtime is not None and runtime.task is not None and not runtime.task.done(),
        "token_hint": _mask_token(token),
    }


async def start_user_wechat_binding(user_id: int) -> dict[str, Any]:
    if not WECHAT_ENABLED:
        raise RuntimeError("WeChat integration is disabled. Set WECHAT_ENABLED=true to use this flow.")

    session = await _get_http_session()
    payload = await _api_get_json(session, "ilink/bot/get_bot_qrcode", params={"bot_type": 3})
    qrcode = payload.get("qrcode", "")
    qrcode_img_content = payload.get("qrcode_img_content") or payload.get("qrcode_url") or ""
    if not qrcode:
        raise RuntimeError("WeChat QR code generation failed")

    session_id = uuid.uuid4().hex
    binding_payload = {
        "session_id": session_id,
        "user_id": user_id,
        "qrcode": qrcode,
        "qrcode_img_content": qrcode_img_content,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await _save_binding_session(session_id, binding_payload)
    await record_audit_event(
        action="channel.wechat.binding_started",
        user_id=user_id,
        tool_name="wechat",
        tool_args={"session_id": session_id},
    )
    return {
        "session_id": session_id,
        "status": "pending",
        "qrcode": qrcode,
        "qrcode_img_content": qrcode_img_content,
        "expires_in": WECHAT_BINDING_TTL_SECONDS,
    }


async def get_user_wechat_binding_session(user_id: int, session_id: str) -> dict[str, Any]:
    binding_payload = await _load_binding_session(session_id)
    if not binding_payload or binding_payload.get("user_id") != user_id:
        return {"status": "expired", "session_id": session_id, "detail": "binding_session_not_found"}

    if binding_payload.get("status") == "bound":
        return {
            "session_id": session_id,
            "status": "bound",
            "connected": True,
            "token_hint": _mask_token(await _get_user_wechat_secret(user_id)),
        }

    session = await _get_http_session()
    status_payload = await _api_get_json(
        session,
        "ilink/bot/get_qrcode_status",
        params={"qrcode": binding_payload["qrcode"]},
    )
    remote_status = status_payload.get("status") or binding_payload.get("status", "pending")

    if remote_status == "confirmed":
        bot_token = status_payload.get("bot_token")
        if not bot_token:
            binding_payload["status"] = "failed"
            await _save_binding_session(session_id, binding_payload)
            await record_audit_event(
                action="channel.wechat.binding_failed",
                user_id=user_id,
                tool_name="wechat",
                tool_args={"session_id": session_id},
                status="FAILURE",
                error_message="confirmed_without_bot_token",
            )
            return {"session_id": session_id, "status": "failed", "detail": "confirmed_without_bot_token"}

        await _upsert_wechat_secret(user_id, bot_token)
        await activate_user_wechat_session(user_id, bot_token=bot_token, base_url=status_payload.get("baseurl"))
        binding_payload["status"] = "bound"
        binding_payload["base_url"] = status_payload.get("baseurl")
        await _save_binding_session(session_id, binding_payload)
        await record_audit_event(
            action="channel.wechat.binding_completed",
            user_id=user_id,
            tool_name="wechat",
            tool_args={"session_id": session_id, "base_url": status_payload.get("baseurl")},
        )
        return {
            "session_id": session_id,
            "status": "bound",
            "connected": True,
            "token_hint": _mask_token(bot_token),
        }

    if remote_status in {"expired", "canceled", "cancelled", "failed"}:
        binding_payload["status"] = "expired" if remote_status == "expired" else "failed"
        await _save_binding_session(session_id, binding_payload)
        return {
            "session_id": session_id,
            "status": binding_payload["status"],
            "detail": remote_status,
            "qrcode_img_content": binding_payload.get("qrcode_img_content"),
        }

    binding_payload["status"] = remote_status
    await _save_binding_session(session_id, binding_payload)
    return {
        "session_id": session_id,
        "status": remote_status,
        "qrcode_img_content": binding_payload.get("qrcode_img_content"),
        "qrcode": binding_payload.get("qrcode"),
    }


async def _ensure_typing_ticket(
    session: aiohttp.ClientSession,
    runtime: WeChatRuntimeSession,
    *,
    user_id: str,
    context_token: str,
) -> str | None:
    ticket = runtime.typing_tickets.get(user_id)
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
        token=runtime.bot_token,
        base_url=runtime.base_url,
    )
    ticket = config_payload.get("typing_ticket")
    if ticket:
        runtime.typing_tickets[user_id] = ticket
    return ticket


async def _send_typing_status(
    session: aiohttp.ClientSession,
    runtime: WeChatRuntimeSession,
    *,
    user_id: str,
    context_token: str,
    status: int,
) -> None:
    ticket = await _ensure_typing_ticket(session, runtime, user_id=user_id, context_token=context_token)
    if not ticket:
        return

    await _api_post_json(
        session,
        "ilink/bot/sendtyping",
        {"ilink_user_id": user_id, "typing_ticket": ticket, "status": status},
        token=runtime.bot_token,
        base_url=runtime.base_url,
    )


async def _handle_inbound_message(runtime: WeChatRuntimeSession, raw_message: dict[str, Any]):
    text = _extract_wechat_text(raw_message)
    if not text:
        return

    from_user_id = str(raw_message.get("from_user_id", ""))
    context_token = raw_message.get("context_token", "")
    if not from_user_id or not context_token:
        logger.warning("Skipping malformed WeChat message: missing from_user_id or context_token.")
        return

    runtime.context_tokens[from_user_id] = context_token
    if runtime.owner_user_id is not None:
        _wechat_channel_user_map[from_user_id] = runtime.owner_user_id

    unified = UnifiedMessage(
        channel=ChannelType.WECHAT,
        channel_id=from_user_id,
        user_id=str(runtime.owner_user_id) if runtime.owner_user_id is not None else None,
        content=text,
        msg_type=MessageType.TEXT,
        meta={
            "username": from_user_id,
            "wechat_username": from_user_id,
            "wechat_from_user_id": from_user_id,
            "wechat_context_token": context_token,
            "wechat_to_user_id": raw_message.get("to_user_id", ""),
            "wechat_message_type": raw_message.get("message_type"),
            "wechat_owner_user_id": runtime.owner_user_id,
        },
    )
    await MQService.push_inbox(unified)
    await record_audit_event(
        action="channel.wechat.message_received",
        user_id=runtime.owner_user_id,
        tool_name="wechat",
        tool_args={"from_user_id": from_user_id, "message_type": raw_message.get("message_type")},
    )


async def _poll_wechat_runtime(runtime: WeChatRuntimeSession):
    session = await _get_http_session()
    logger.info("Starting WeChat polling loop for session %s", runtime.session_key)

    while True:
        try:
            result = await _api_post_json(
                session,
                "ilink/bot/getupdates",
                {
                    "get_updates_buf": runtime.get_updates_buf,
                    "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
                },
                token=runtime.bot_token,
                base_url=runtime.base_url,
            )
            runtime.get_updates_buf = result.get("get_updates_buf") or runtime.get_updates_buf

            for raw_message in result.get("msgs") or []:
                await _handle_inbound_message(runtime, raw_message)

            await asyncio.sleep(WECHAT_POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("WeChat polling loop error for session %s: %s", runtime.session_key, exc, exc_info=True)
            await asyncio.sleep(max(WECHAT_POLL_INTERVAL_SECONDS, 1.0))


async def activate_user_wechat_session(
    user_id: int | None,
    *,
    bot_token: str,
    base_url: str | None = None,
) -> WeChatRuntimeSession:
    session_key = _runtime_session_key(user_id)
    runtime = _wechat_runtime_sessions.get(session_key)
    if runtime and runtime.task and not runtime.task.done():
        runtime.bot_token = bot_token
        runtime.base_url = base_url
        return runtime

    runtime = WeChatRuntimeSession(
        session_key=session_key,
        owner_user_id=user_id,
        bot_token=bot_token,
        base_url=base_url,
    )
    runtime.task = asyncio.create_task(_poll_wechat_runtime(runtime))
    _wechat_runtime_sessions[session_key] = runtime
    await record_audit_event(
        action="channel.wechat.login_completed",
        user_id=user_id,
        tool_name="wechat",
        tool_args={"mode": "bound_session" if user_id is not None else "legacy_env"},
    )
    return runtime


async def send_wechat_message(msg: UnifiedMessage):
    session_owner_id = _wechat_channel_user_map.get(msg.channel_id)
    if session_owner_id is None and msg.user_id:
        try:
            session_owner_id = int(msg.user_id)
        except (TypeError, ValueError):
            session_owner_id = None

    runtime = _wechat_runtime_sessions.get(_runtime_session_key(session_owner_id))
    if runtime is None and session_owner_id is not None:
        bot_token = await _get_user_wechat_secret(session_owner_id)
        if bot_token:
            runtime = await activate_user_wechat_session(session_owner_id, bot_token=bot_token)

    if runtime is None:
        logger.warning("No WeChat runtime session is available for outbound message to %s.", msg.channel_id)
        return

    session = await _get_http_session()
    target_user_id = msg.channel_id
    context_token = runtime.context_tokens.get(target_user_id)

    if msg.msg_type == MessageType.ACTION:
        if msg.content == "typing" and context_token:
            await _send_typing_status(session, runtime, user_id=target_user_id, context_token=context_token, status=1)
        return

    if not context_token:
        logger.warning("No WeChat context token cached for %s; skipping outbound message.", target_user_id)
        return

    await _send_typing_status(session, runtime, user_id=target_user_id, context_token=context_token, status=1)
    payload = _build_sendmessage_payload(
        to_user_id=target_user_id,
        context_token=context_token,
        text=msg.content,
    )
    await _api_post_json(
        session,
        "ilink/bot/sendmessage",
        payload,
        token=runtime.bot_token,
        base_url=runtime.base_url,
    )
    await _send_typing_status(session, runtime, user_id=target_user_id, context_token=context_token, status=2)
    await record_audit_event(
        action="channel.wechat.message_sent",
        user_id=runtime.owner_user_id,
        tool_name="wechat",
        tool_args={"to_user_id": target_user_id, "message_type": msg.msg_type.value},
    )


async def run_wechat_bot():
    if not WECHAT_ENABLED:
        logger.info("WECHAT_ENABLED is false. WeChat interface disabled.")
        return

    global _dispatcher_registered
    if not _dispatcher_registered:
        InterfaceDispatcher.register_handler(ChannelType.WECHAT, send_wechat_message)
        _dispatcher_registered = True

    for user_id, bot_token in await _list_bound_wechat_tokens():
        await activate_user_wechat_session(user_id, bot_token=bot_token)

    logger.info("WeChat adapter initialized with %s active runtime session(s).", len(_wechat_runtime_sessions))
