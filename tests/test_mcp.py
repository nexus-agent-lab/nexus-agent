"""
Tests for MCP tool loading and execution.
"""

import pytest

from app.core.mcp_manager import MCPManager


@pytest.mark.asyncio
class TestMCPManager:
    """Tests for MCP Manager functionality."""

    async def test_get_system_instructions(self):
        """MCP Manager should aggregate system instructions."""
        instructions = MCPManager.get_system_instructions()
        assert isinstance(instructions, str)

    async def test_mcp_tools_loading(self):
        """MCP tools should load without errors."""
        try:
            from app.core.mcp_manager import get_mcp_tools

            tools = await get_mcp_tools()
            assert isinstance(tools, list)
        except Exception as e:
            # Expected to fail in test environment without MCP servers
            pytest.skip(f"MCP servers not available: {e}")


class TestMCPMiddleware:
    """Tests for MCP Middleware caching and throttling."""

    def test_cache_key_generation(self):
        """Middleware should generate consistent cache keys."""
        from app.core.mcp_middleware import MCPMiddleware

        args1 = {"param": "value"}
        args2 = {"param": "value"}

        key1 = MCPMiddleware._get_cache_key("test_tool", args1)
        key2 = MCPMiddleware._get_cache_key("test_tool", args2)

        assert key1 == key2

    def test_response_threshold_detection(self):
        """Middleware should detect model context capabilities."""
        import os

        from app.core.mcp_middleware import MCPMiddleware

        # Test GLM-4 detection
        os.environ["LLM_MODEL"] = "glm-4.7-flash"
        os.environ["LLM_BASE_URL"] = "http://localhost:11434"
        threshold = MCPMiddleware._get_response_threshold()
        assert threshold == MCPMiddleware.THRESHOLD_LOCAL_LARGE

        # Test cloud detection
        os.environ["LLM_BASE_URL"] = "https://api.openai.com"
        threshold = MCPMiddleware._get_response_threshold()
        assert threshold >= MCPMiddleware.THRESHOLD_CLOUD_GLM

    def test_cache_key_excludes_secrets(self):
        """Cache key should not change when secrets are injected."""
        from app.core.mcp_middleware import MCPMiddleware

        args = {"param": "value"}
        key_before = MCPMiddleware._get_cache_key("test_tool", args)

        args_injected = {"param": "value", "api_key": "secret_val"}
        key_after = MCPMiddleware._get_cache_key("test_tool", args_injected, injected_keys=["api_key"])

        assert key_before == key_after
