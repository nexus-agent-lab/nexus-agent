import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.auth_service import AuthService, BindAttemptOutcome, BindResult
from app.models.user import User


class TestTelegramAuthHandoff:
    def test_start_telegram_login_requires_bot_username(self, api_client: TestClient, mocker):
        mocker.patch(
            "app.api.auth.os.getenv",
            side_effect=lambda key, default=None: None if key == "TELEGRAM_BOT_USERNAME" else default,
        )

        response = api_client.post("/api/auth/telegram/start")

        assert response.status_code == 503
        assert response.json()["detail"] == "Telegram bot username is not configured"

    def test_start_telegram_login_returns_challenge(self, api_client: TestClient, mocker):
        mocker.patch(
            "app.api.auth.os.getenv",
            side_effect=lambda key, default=None: "nexus_test_bot" if key == "TELEGRAM_BOT_USERNAME" else default,
        )
        mocker.patch(
            "app.api.auth.AuthService.create_telegram_login_challenge",
            return_value={
                "challenge_id": "challenge-1",
                "csrf_token": "csrf-1",
                "expires_in": 300,
                "telegram_deep_link_url": "https://t.me/nexus_test_bot?start=login_challenge-1",
            },
        )

        response = api_client.post("/api/auth/telegram/start")

        assert response.status_code == 200
        payload = response.json()
        assert payload["challenge_id"] == "challenge-1"
        assert payload["csrf_token"] == "csrf-1"
        assert payload["telegram_deep_link_url"].endswith("login_challenge-1")

    def test_complete_telegram_login_rejects_invalid_exchange(self, api_client: TestClient, mocker):
        mocker.patch("app.api.auth.AuthService.consume_telegram_login_exchange", return_value=None)

        response = api_client.post(
            "/api/auth/telegram/complete",
            json={"challenge_id": "challenge-1", "exchange_token": "bad", "csrf_token": "csrf-1"},
        )

        assert response.status_code == 400
        assert "Invalid, expired, or already used" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_complete_telegram_login_issues_jwt(self, api_client: TestClient, test_user: User, mocker):
        mocker.patch("app.api.auth.AuthService.consume_telegram_login_exchange", return_value=test_user.id)

        response = api_client.post(
            "/api/auth/telegram/complete",
            json={"challenge_id": "challenge-1", "exchange_token": "good", "csrf_token": "csrf-1"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["token_type"] == "bearer"
        decoded = jwt.decode(payload["access_token"], options={"verify_signature": False})
        assert decoded["sub"] == str(test_user.id)
        assert decoded["username"] == test_user.username

    def test_telegram_login_status_surfaces_structured_next_step(self, api_client: TestClient, mocker):
        mocker.patch(
            "app.api.auth.AuthService.get_telegram_login_status",
            return_value={
                "status": "rejected_unbound",
                "exchange_token": None,
                "detail": "This Telegram account is not linked to Nexus yet.",
                "next_step": "bind_telegram",
            },
        )

        response = api_client.get("/api/auth/telegram/status", params={"challenge_id": "challenge-1"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "rejected_unbound"
        assert payload["next_step"] == "bind_telegram"
        assert "not linked" in payload["detail"]


def test_describe_bind_attempt_maps_result_to_message_key():
    outcome: BindAttemptOutcome = AuthService.describe_bind_attempt(BindResult.PROVIDER_CONFLICT, user_id=42)
    assert outcome.status == "provider_conflict"
    assert outcome.message_key == "bind_conflict_provider"
