from app.interfaces.wechat import _build_sendmessage_payload, _extract_wechat_text, _make_headers


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
