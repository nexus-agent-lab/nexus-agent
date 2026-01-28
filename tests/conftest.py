"""
Shared test fixtures and configuration for the Nexus Agent test suite.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up test environment variables BEFORE importing app
os.environ["LLM_MODEL"] = "gpt-4o-mini"
os.environ["LLM_BASE_URL"] = "http://localhost:8000"
os.environ["LLM_API_KEY"] = "sk-dummy"
os.environ["OPENAI_API_KEY"] = "sk-dummy"
# Use file-based sqlite for sharing between app and test fixtures
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.core.db import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402

# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a file-based SQLite database for testing."""
    # Ensure any previous test.db is removed for isolation
    if os.path.exists("test.db"):
        os.remove("test.db")

    engine = create_async_engine(
        "sqlite+aiosqlite:///test.db",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create a test user."""
    user = User(username="testuser", role="user", telegram_id=123456789, api_key="test_key")
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(username="admin", role="admin", telegram_id=987654321, api_key="admin_key")
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


# ============================================================================
# API Client Fixtures
# ============================================================================


@pytest.fixture
def api_client(test_db: AsyncSession, mocker) -> TestClient:
    """Provide a FastAPI test client with dependency overrides/lifespan."""
    # Mock memory search globally for API tests to avoid connection errors
    mocker.patch("app.core.memory.memory_manager.search_memory", return_value=[])

    async def _get_test_session():
        yield test_db

    app.dependency_overrides[get_session] = _get_test_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

    # Cleanup database file after test
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except PermissionError:
            pass


# ============================================================================
# Mock LLM Fixtures
# ============================================================================


class MockLLM:
    """Mock LLM for predictable testing."""

    def __init__(self, responses: list[str] = None):
        self.responses = responses or ["Mock response"]
        self.call_count = 0

    async def ainvoke(self, messages, **kwargs):
        """Return a predictable response."""
        from langchain_core.messages import AIMessage

        response = self.responses[min(self.call_count, len(self.responses) - 1)]
        self.call_count += 1
        return AIMessage(content=response)

    def bind_tools(self, tools):
        """Mock tool binding."""
        return self


@pytest.fixture
def mock_llm():
    """Provide a mock LLM instance."""
    return MockLLM()


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def test_env():
    """Environment is already set at module level."""
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"
    yield
