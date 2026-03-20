from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.interfaces.telegram import start


def _make_update(start_text: str = "/start login_test"):
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=123456, username="alice", first_name="Alice", language_code="en"),
        effective_chat=SimpleNamespace(id=987654),
        message=SimpleNamespace(text=start_text, reply_markdown=AsyncMock()),
    )


def _make_context(args: list[str]):
    return SimpleNamespace(args=args, bot=SimpleNamespace(set_my_commands=AsyncMock()))


@pytest.mark.asyncio
async def test_start_login_handoff_approves_for_bound_user(mocker):
    update = _make_update()
    context = _make_context(["login_test"])
    bound_user = SimpleNamespace(id=42, role="user", language="en")

    mocker.patch("app.interfaces.telegram.get_user_language", AsyncMock(return_value="en"))
    mocker.patch("app.interfaces.telegram.AuthService.get_user_by_identity", AsyncMock(return_value=bound_user))
    approve_mock = mocker.patch(
        "app.interfaces.telegram.AuthService.approve_telegram_login_challenge",
        AsyncMock(return_value="exchange-token"),
    )
    refresh_mock = mocker.patch("app.interfaces.telegram.refresh_user_commands", AsyncMock())

    await start(update, context)

    approve_mock.assert_awaited_once_with("test", 42, "123456")
    refresh_mock.assert_awaited_once()
    update.message.reply_markdown.assert_awaited_once()
    assert "return to the browser" in update.message.reply_markdown.await_args.args[0]


@pytest.mark.asyncio
async def test_start_login_handoff_requires_existing_binding(mocker):
    update = _make_update()
    context = _make_context(["login_test"])

    mocker.patch("app.interfaces.telegram.get_user_language", AsyncMock(return_value="en"))
    mocker.patch("app.interfaces.telegram.AuthService.get_user_by_identity", AsyncMock(return_value=None))
    reject_mock = mocker.patch(
        "app.interfaces.telegram.AuthService.reject_telegram_login_challenge",
        AsyncMock(return_value=True),
    )
    approve_mock = mocker.patch(
        "app.interfaces.telegram.AuthService.approve_telegram_login_challenge",
        AsyncMock(return_value=None),
    )

    await start(update, context)

    reject_mock.assert_awaited_once_with("test", "rejected_unbound")
    approve_mock.assert_not_awaited()
    update.message.reply_markdown.assert_awaited_once()
    assert "not linked yet" in update.message.reply_markdown.await_args.args[0]
