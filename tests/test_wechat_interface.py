from unittest.mock import AsyncMock

import pytest

from app.core.mq import MessageType, UnifiedMessage
from app.interfaces import wechat
from app.interfaces.wechat import (
    _build_sendmessage_payload,
    _extract_wechat_text,
    _make_headers,
    get_user_wechat_binding_session,
    start_user_wechat_binding,
)


def test_make_headers_sets_required_wechat_headers():
    headers = _make_headers("token-123")

    assert headers["AuthorizationType"] == "ilink_bot_token"
    assert headers["Authorization"] == "Bearer token-123"
    assert headers["Content-Type"] == "application/json"
    assert headers["X-WECHAT-UIN"]


def test_extract_wechat_text_returns_first_text_item():
    text = _extract_wechat_text(
        {
            "message_type": 1,
            "item_list": [
                {"type": 1, "text_item": {"text": "hello from wechat"}},
            ],
        }
    )

    assert text == "hello from wechat"


def test_build_sendmessage_payload_matches_ilink_shape():
    payload = _build_sendmessage_payload(
        to_user_id="alice@im.wechat",
        context_token="ctx-123",
        text="pong",
    )

    msg = payload["msg"]
    assert msg["to_user_id"] == "alice@im.wechat"
    assert msg["context_token"] == "ctx-123"
    assert msg["message_type"] == 2
    assert msg["message_state"] == 2
    assert msg["item_list"][0]["text_item"]["text"] == "pong"
    assert payload["base_info"]["channel_version"]


@pytest.mark.asyncio
async def test_start_user_wechat_binding_returns_qrcode_payload(mocker):
    mocker.patch.object(wechat, "WECHAT_ENABLED", True)
    mocker.patch("app.interfaces.wechat._get_http_session", AsyncMock(return_value=object()))
    mocker.patch(
        "app.interfaces.wechat._api_get_json",
        AsyncMock(return_value={"qrcode": "qr-123", "qrcode_img_content": "https://example.com/qr.png"}),
    )
    save_mock = mocker.patch("app.interfaces.wechat._save_binding_session", AsyncMock())
    audit_mock = mocker.patch("app.interfaces.wechat.record_audit_event", AsyncMock())

    payload = await start_user_wechat_binding(7)

    assert payload["status"] == "pending"
    assert payload["qrcode"] == "qr-123"
    assert payload["qrcode_img_content"] == "https://example.com/qr.png"
    save_mock.assert_awaited_once()
    audit_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_wechat_binding_session_confirms_and_activates_runtime(mocker):
    mocker.patch(
        "app.interfaces.wechat._load_binding_session",
        AsyncMock(
            return_value={
                "session_id": "sess-1",
                "user_id": 7,
                "qrcode": "qr-123",
                "status": "pending",
            }
        ),
    )
    mocker.patch("app.interfaces.wechat._get_http_session", AsyncMock(return_value=object()))
    mocker.patch(
        "app.interfaces.wechat._api_get_json",
        AsyncMock(
            return_value={"status": "confirmed", "bot_token": "bot-token-123", "baseurl": wechat.WECHAT_BASE_URL}
        ),
    )
    mocker.patch("app.interfaces.wechat._upsert_wechat_secret", AsyncMock())
    activate_mock = mocker.patch("app.interfaces.wechat.activate_user_wechat_session", AsyncMock())
    save_mock = mocker.patch("app.interfaces.wechat._save_binding_session", AsyncMock())
    audit_mock = mocker.patch("app.interfaces.wechat.record_audit_event", AsyncMock())

    payload = await get_user_wechat_binding_session(7, "sess-1")

    assert payload["status"] == "bound"
    assert payload["connected"] is True
    activate_mock.assert_awaited_once_with(7, bot_token="bot-token-123", base_url=wechat.WECHAT_BASE_URL)
    save_mock.assert_awaited_once()
    audit_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_wechat_message_uses_runtime_session_selected_by_channel_map(mocker):
    runtime = wechat.WeChatRuntimeSession(session_key="user:7", owner_user_id=7, bot_token="bot-token")
    runtime.context_tokens["alice@im.wechat"] = "ctx-123"
    wechat._wechat_runtime_sessions["user:7"] = runtime
    wechat._wechat_channel_user_map["alice@im.wechat"] = 7

    mocker.patch("app.interfaces.wechat._get_http_session", AsyncMock(return_value=object()))
    typing_mock = mocker.patch("app.interfaces.wechat._send_typing_status", AsyncMock())
    post_mock = mocker.patch("app.interfaces.wechat._api_post_json", AsyncMock(return_value={}))
    audit_mock = mocker.patch("app.interfaces.wechat.record_audit_event", AsyncMock())

    await wechat.send_wechat_message(
        UnifiedMessage(
            channel=wechat.ChannelType.WECHAT,
            channel_id="alice@im.wechat",
            content="hello",
            msg_type=MessageType.TEXT,
        )
    )

    assert typing_mock.await_count == 2
    post_mock.assert_awaited_once()
    audit_mock.assert_awaited_once()
    wechat._wechat_runtime_sessions.clear()
    wechat._wechat_channel_user_map.clear()
