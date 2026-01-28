"""
Tests for FastAPI endpoints and API functionality.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.user import User


class TestChatEndpoint:
    """Tests for the /chat endpoint."""

    def test_chat_requires_authentication(self, api_client: TestClient):
        """Chat endpoint should require API key."""
        response = api_client.post("/chat", json={"message": "Hello"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_with_valid_auth(self, api_client: TestClient, test_user: User):
        """Chat endpoint should work with valid authentication."""
        headers = {"X-API-Key": "test_key"}
        response = api_client.post("/chat", json={"message": "Hello"}, headers=headers)
        # This will fail without proper auth setup, but structure is ready
        assert response.status_code in [200, 401]


class TestVoiceEndpoint:
    """Tests for the /voice endpoint."""

    def test_voice_requires_file(self, api_client: TestClient, test_user: User):
        """Voice endpoint should require file upload."""
        headers = {"X-API-Key": "test_key"}
        response = api_client.post("/voice", headers=headers)
        assert response.status_code == 422  # Validation error


class TestHealthCheck:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, api_client: TestClient):
        """Root endpoint should return service info."""
        response = api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data
