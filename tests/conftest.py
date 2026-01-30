"""
Shared test fixtures and configuration for the Nexus Agent test suite.
"""

# noqa: E402 (Standard for test configuration)
import asyncio
import os
import shutil
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

import app.core.db
import app.core.session
import tests.test_env_setup as env_setup  # noqa: F401
from app.core.db import get_session
from app.main import app as fastapi_app
from app.models.user import User
from tests.test_env_setup import TEST_DB_DIR, TEST_DB_PATH

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
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{TEST_DB_PATH}",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # PATCH app.core.db.AsyncSessionLocal to use our test engine
    # This ensures background tasks (SessionManager) use the same DB
    original_engine = app.core.db.engine
    app.core.db.engine = engine
    original_sessionmaker = app.core.db.AsyncSessionLocal
    app.core.db.AsyncSessionLocal = async_session

    # Also patch app.core.session because it imported AsyncSessionLocal
    original_session_sessionmaker = getattr(app.core.session, "AsyncSessionLocal", None)
    app.core.session.AsyncSessionLocal = async_session

    async with async_session() as session:
        yield session

    # Restore
    app.core.db.engine = original_engine
    app.core.db.AsyncSessionLocal = original_sessionmaker
    if original_session_sessionmaker:
        app.core.session.AsyncSessionLocal = original_session_sessionmaker
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

    fastapi_app.dependency_overrides[get_session] = _get_test_session
    with TestClient(fastapi_app) as client:
        yield client
    fastapi_app.dependency_overrides.clear()

    # Cleanup database file after test
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
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
    """Cleanup test directories after session."""
    yield
    if os.path.exists(TEST_DB_DIR):
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def mock_background_services(mocker):
    """Prevent background services from starting during tests."""
    mocker.patch("app.interfaces.telegram.run_telegram_bot", return_value=None)
    mocker.patch("app.interfaces.feishu.run_feishu_bot", return_value=None)
    mocker.patch("app.core.scheduler.SchedulerService.start", return_value=None)
    mocker.patch("app.core.scheduler.SchedulerService.stop", return_value=None)
    mocker.patch("app.core.worker.AgentWorker.start", return_value=None)
    mocker.patch("app.core.worker.AgentWorker.stop", return_value=None)
    mocker.patch("app.core.dispatcher.InterfaceDispatcher.start", return_value=None)
    mocker.patch("app.core.dispatcher.InterfaceDispatcher.stop", return_value=None)
