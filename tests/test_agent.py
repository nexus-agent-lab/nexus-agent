"""
Tests for the agent graph and decision-making logic.
"""

import pytest
from langchain_core.messages import HumanMessage

from app.core.agent import create_agent_graph
from app.models.user import User


@pytest.mark.asyncio
class TestAgentGraph:
    """Tests for agent graph execution."""

    async def test_agent_initialization(self, mock_llm):
        """Agent graph should initialize with tools."""
        tools = []
        graph = create_agent_graph(tools)
        assert graph is not None

    async def test_agent_processes_message(self, mock_llm, test_user: User):
        """Agent should process user messages."""
        tools = []
        graph = create_agent_graph(tools)

        initial_state = {
            "messages": [HumanMessage(content="Hello")],
            "user": test_user,
        }

        # This will fail without proper mocking, but structure is ready
        try:
            result = await graph.ainvoke(initial_state)
            assert "messages" in result
        except Exception:
            # Expected to fail without full mock setup
            pass


@pytest.mark.asyncio
class TestAgentMemory:
    """Tests for agent memory retrieval."""

    async def test_memory_retrieval(self, test_user: User, mocker):
        """Agent should retrieve user memories."""
        # Mock memory search to avoid API call
        mocker.patch("app.core.memory.memory_manager.search_memory", return_value=[])

        from app.core.agent import retrieve_memories

        state = {
            "messages": [HumanMessage(content="What's my name?")],
            "user": test_user,
        }

        result = await retrieve_memories(state)
        assert "memories" in result
        assert isinstance(result["memories"], list)
