from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.tool_router import SemanticToolRouter


class MockTool:
    def __init__(self, name, required_role=None):
        self.name = name
        self.required_role = required_role
        self.description = f"Description for {name}"
        # Some tools use func.required_role
        self.func = MagicMock()
        if required_role:
            self.func.required_role = required_role


@pytest.mark.asyncio
async def test_router_role_filtering():
    router = SemanticToolRouter()
    # Bypass init
    router._initialized = True
    router.embeddings = AsyncMock()
    router.tool_index = None  # Disable semantic search for now, just test check_role

    # Mock tools
    admin_tool = MockTool("admin_only", "admin")
    user_tool = MockTool("user_tool", "user")
    no_role_tool = MockTool("public_tool", None)

    # Test 1: Admin user
    assert router._check_role(admin_tool, "admin")
    assert router._check_role(user_tool, "admin")
    assert router._check_role(no_role_tool, "admin")

    # Test 2: Regular user
    assert not router._check_role(admin_tool, "user")
    assert router._check_role(user_tool, "user")
    assert router._check_role(no_role_tool, "user")

    # Test 3: Guest
    assert not router._check_role(admin_tool, "guest")
    assert router._check_role(user_tool, "guest")


@pytest.mark.asyncio
async def test_route_fallback_filtering():
    """Verify fallback (empty query) respects roles"""
    router = SemanticToolRouter()
    router._initialized = True
    router.embeddings = AsyncMock()

    admin_tool = MockTool("admin_only", "admin")
    user_tool = MockTool("user_tool", "user")

    router.all_tools = [admin_tool, user_tool]
    router.core_tools = [admin_tool, user_tool]

    # Test Admin
    results = await router.route("", role="admin")
    assert len(results) == 2

    # Test User
    results = await router.route("", role="user")
    assert len(results) == 1
    assert results[0].name == "user_tool"
