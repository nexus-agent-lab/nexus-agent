from app.core.mq import ChannelType, UnifiedMessage
from app.core.worker import AgentWorker


def test_bind_command_detection_accepts_plain_bind_text():
    assert AgentWorker._is_bind_command("bind 123456")
    assert AgentWorker._is_bind_command("/bind 123456")
    assert AgentWorker._is_bind_command("绑定 123456")
    assert not AgentWorker._is_bind_command("hello there")


def test_extract_provider_identity_prefers_wechat_sender_metadata():
    msg = UnifiedMessage(
        channel=ChannelType.WECHAT,
        channel_id="fallback-channel-id",
        content="bind 123456",
        meta={"wechat_from_user_id": "alice@im.wechat"},
    )

    assert AgentWorker._extract_provider_identity(msg) == "alice@im.wechat"


def test_extract_provider_username_reuses_wechat_identity_when_present():
    msg = UnifiedMessage(
        channel=ChannelType.WECHAT,
        channel_id="fallback-channel-id",
        content="hi",
        meta={"wechat_from_user_id": "alice@im.wechat"},
    )

    assert AgentWorker._extract_provider_username(msg) == "alice@im.wechat"
