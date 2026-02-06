import asyncio
import os

import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


def get_db_url(sync: bool = True) -> str:
    """
    Returns the database URL from environment variables.
    If sync=True, ensures the URL is compatible with standard SQLAlchemy (strips asyncpg).
    """
    url = os.getenv("DATABASE_URL", "postgresql://nexus:nexus_password@postgres:5432/nexus_db")
    if sync:
        return url.replace("postgresql+asyncpg://", "postgresql://")
    else:
        # Ensure it has the async driver if requested
        if "asyncpg" not in url:
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url


@st.cache_resource
def get_sync_engine():
    """Returns a cached sync engine."""
    url = get_db_url(sync=True)
    return create_engine(url)


def get_async_session_maker():
    """
    Returns an async sessionmaker.
    We do NOT cache the async engine/sessionmaker to avoid event loop affinity issues
    (e.g., 'Future attached to a different loop').
    We use NullPool to ensure connections are closed promptly and don't leak across loops.
    """
    url = get_db_url(sync=False)
    engine = create_async_engine(url, poolclass=NullPool)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@st.cache_resource
def get_engine(sync: bool = True):
    """
    Deprecated for async: use get_async_session_maker instead.
    Still works for sync legacy calls.
    """
    if sync:
        return get_sync_engine()
    else:
        # Fallback for old calls, but not recommended
        url = get_db_url(sync=False)
        return create_async_engine(url, poolclass=NullPool)


def run_async(coro):
    """
    Helper to run async coroutines in a synchronous Streamlit context.
    """
    return asyncio.run(coro)


def get_api_url() -> str:
    """
    Returns the backend API URL.
    """
    return os.getenv("API_URL", "http://localhost:8000")
