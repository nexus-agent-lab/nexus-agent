from unittest.mock import AsyncMock

import pytest
from langchain_core.tools import Tool

from app.core.tool_router import SemanticToolRouter


@pytest.mark.asyncio
async def test_semantic_router():
    router = SemanticToolRouter()

    # Mock Embeddings
    mock_embeddings = AsyncMock()
    # Mock behavior: "check weather" -> [1.0, 0.0], "write code" -> [0.0, 1.0]
    # Tools: Weather -> [1.0, 0.1], Sandbox -> [0.1, 1.0]

    # But real implementation handles arbitrary vectors.
    # Let's just mock aembed_documents to return fixed vectors
    mock_embeddings.aembed_documents.return_value = [
        [1.0, 0.0, 0.0],  # Tool 1: Weather
        [0.0, 1.0, 0.0],  # Tool 2: Sandbox
        [0.0, 0.0, 1.0],  # Tool 3: Irrelevant
    ]

    mock_embeddings.aembed_query.side_effect = lambda q: ([1.0, 0.0, 0.0] if "weather" in q else [0.0, 1.0, 0.0])

    router.embeddings = mock_embeddings

    # Define Tools
    tool1 = Tool(name="get_weather", description="Check weather", func=lambda: None)
    tool2 = Tool(name="python_sandbox", description="Run code", func=lambda: None)  # Core in real app, but here...
    tool3 = Tool(name="random_tool", description="Do nothing", func=lambda: None)

    # Override CORE_TOOL_NAMES for test to isolate logic
    import app.core.tool_router

    original_core = app.core.tool_router.CORE_TOOL_NAMES
    app.core.tool_router.CORE_TOOL_NAMES = {"time"}  # minimal core

    try:
        # Register
        tools = [tool1, tool2, tool3]
        await router.register_tools(tools)

        # Test 1: Route for Weather
        selected = await router.route("check weather")
        names = [t.name for t in selected]
        assert "get_weather" in names
        assert "random_tool" not in names  # Should be filtered out by low score

        # Test 2: Core tool always present?
        # We need to add a core tool to list
        tool_core = Tool(name="time", description="Get time", func=lambda: None)
        await router.register_tools([tool1, tool2, tool3, tool_core])

        selected = await router.route("check weather")
        names = [t.name for t in selected]
        assert "time" in names  # Core
        assert "get_weather" in names  # Semantic match

    finally:
        app.core.tool_router.CORE_TOOL_NAMES = original_core
