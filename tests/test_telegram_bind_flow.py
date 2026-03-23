from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.auth_service import BindResult
from app.interfaces.telegram import process_bind_token


def _make_update():
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=123456, username="alice", first_name="Alice", language_code="en"),
        effective_chat=SimpleNamespace(id=987654),
    )


def _make_context():
    return SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()), user_data={})


class _AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.asyncio
async def test_process_bind_token_success_updates_menu(mocker):
    update = _make_update()
    context = _make_context()

    mocker.patch("app.interfaces.telegram.AuthService.verify_bind_token", AsyncMock(return_value=42))
    mocker.patch("app.interfaces.telegram.AuthService.bind_identity", AsyncMock(return_value=BindResult.SUCCESS))
    mocker.patch(
        "app.interfaces.telegram.AuthService.get_user_by_identity",
        AsyncMock(return_value=SimpleNamespace(role="user")),
    )
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=SimpleNamespace(language="en"))
    mock_session.commit = AsyncMock()
    mock_session.add = lambda _value: None
    mocker.patch(
        "app.core.db.AsyncSessionLocal",
        return_value=_AsyncSessionContext(mock_session),
    )
    refresh_mock = mocker.patch("app.interfaces.telegram.refresh_user_commands", AsyncMock())

    await process_bind_token(update, context, "123456", "en")

    context.bot.send_message.assert_awaited_once()
    kwargs = context.bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == "987654"
    assert "linked to Nexus User #42" in kwargs["text"]
    refresh_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_bind_token_invalid_token(mocker):
    update = _make_update()
    context = _make_context()

    mocker.patch("app.interfaces.telegram.AuthService.verify_bind_token", AsyncMock(return_value=None))
    audit_mock = mocker.patch("app.interfaces.telegram.record_audit_event", AsyncMock())

    await process_bind_token(update, context, "000000", "en")

    context.bot.send_message.assert_awaited_once()
    kwargs = context.bot.send_message.await_args.kwargs
    assert "Invalid or expired bind code" in kwargs["text"]
    audit_mock.assert_awaited_once()
    assert audit_mock.await_args.kwargs["action"] == "auth.binding_failed"


@pytest.mark.asyncio
async def test_process_bind_token_provider_conflict(mocker):
    update = _make_update()
    context = _make_context()

    mocker.patch("app.interfaces.telegram.AuthService.verify_bind_token", AsyncMock(return_value=42))
    mocker.patch(
        "app.interfaces.telegram.AuthService.bind_identity",
        AsyncMock(return_value=BindResult.PROVIDER_CONFLICT),
    )
    audit_mock = mocker.patch("app.interfaces.telegram.record_audit_event", AsyncMock())
    refresh_mock = mocker.patch("app.interfaces.telegram.refresh_user_commands", AsyncMock())

    await process_bind_token(update, context, "123456", "en")

    context.bot.send_message.assert_awaited_once()
    kwargs = context.bot.send_message.await_args.kwargs
    assert "already linked to another Nexus User" in kwargs["text"]
    refresh_mock.assert_not_awaited()
    audit_mock.assert_awaited_once()
    assert audit_mock.await_args.kwargs["action"] == "auth.binding_conflict"


@pytest.mark.asyncio
async def test_process_bind_token_user_conflict(mocker):
    update = _make_update()
    context = _make_context()

    mocker.patch("app.interfaces.telegram.AuthService.verify_bind_token", AsyncMock(return_value=42))
    mocker.patch(
        "app.interfaces.telegram.AuthService.bind_identity",
        AsyncMock(return_value=BindResult.USER_CONFLICT),
    )
    audit_mock = mocker.patch("app.interfaces.telegram.record_audit_event", AsyncMock())
    refresh_mock = mocker.patch("app.interfaces.telegram.refresh_user_commands", AsyncMock())

    await process_bind_token(update, context, "123456", "en")

    context.bot.send_message.assert_awaited_once()
    kwargs = context.bot.send_message.await_args.kwargs
    assert "already linked to another Telegram account" in kwargs["text"]
    refresh_mock.assert_not_awaited()
    audit_mock.assert_awaited_once()
    assert audit_mock.await_args.kwargs["action"] == "auth.binding_conflict"
