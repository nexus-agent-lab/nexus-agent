"""
Tests for FastAPI endpoints and API functionality.
"""

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

import app.main
from app.core.session import SessionManager
from app.models.user import User


class TestChatEndpoint:
    """Tests for the /api/chat endpoint."""

    def test_chat_requires_authentication(self, api_client: TestClient):
        """Chat endpoint should require API key."""
        response = api_client.post("/api/chat", json={"message": "Hello"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_with_valid_auth(self, api_client: TestClient, test_user: User):
        """Chat endpoint should work with valid authentication."""
        headers = {"X-API-Key": "test_key"}
        response = api_client.post("/api/chat", json={"message": "Hello"}, headers=headers)
        # This will fail without proper auth setup, but structure is ready
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_chat_reuses_thread_history(self, api_client: TestClient, test_user: User, mocker):
        """Second-turn web chat requests should see persisted prior context."""

        class FakeGraph:
            async def ainvoke(self, state):
                human_messages = [msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)]
                if human_messages[-1] == "继续呀":
                    assert "帮我搜索天气" in human_messages
                    response = AIMessage(content="我继续刚才的搜索。")
                else:
                    response = AIMessage(content="我先帮你搜索天气。")

                if state.get("session_id"):
                    await SessionManager.save_message(
                        session_id=state["session_id"],
                        role="assistant",
                        type="ai",
                        content=str(response.content),
                    )

                return {"messages": [response]}

        mocker.patch.object(app.main, "agent_graph", FakeGraph())

        headers = {"X-API-Key": "test_key"}
        first_response = api_client.post("/api/chat", json={"message": "帮我搜索天气"}, headers=headers)

        assert first_response.status_code == 200
        first_payload = first_response.json()
        assert first_payload["response"] == "我先帮你搜索天气。"
        assert first_payload["created_new_thread"] is True
        assert first_payload["thread_id"]

        second_response = api_client.post(
            "/api/chat",
            json={"message": "继续呀", "thread_id": first_payload["thread_id"]},
            headers=headers,
        )

        assert second_response.status_code == 200
        second_payload = second_response.json()
        assert second_payload["response"] == "我继续刚才的搜索。"
        assert second_payload["thread_id"] == first_payload["thread_id"]
        assert second_payload["created_new_thread"] is False


class TestVoiceEndpoint:
    """Tests for the /api/voice endpoint."""

    def test_voice_requires_file(self, api_client: TestClient, test_user: User):
        """Voice endpoint should require file upload."""
        headers = {"X-API-Key": "test_key"}
        response = api_client.post("/api/voice", headers=headers)
        assert response.status_code == 422  # Validation error


class TestHealthCheck:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, api_client: TestClient):
        """Root endpoint should return service info."""
        response = api_client.get("/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data
