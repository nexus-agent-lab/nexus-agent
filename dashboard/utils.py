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
def get_engine(sync: bool = True):
    """
    Returns a cached SQLAlchemy engine.
    """
    url = get_db_url(sync=sync)
    if sync:
        return create_engine(url)
    else:
        # Async engine usually doesn't need st.cache_resource if handled by sessionmaker,
        # but for consistency we can cache the engine instance.
        return create_async_engine(url, poolclass=NullPool)


def get_async_session_maker():
    """
    Returns an async sessionmaker.
    """
    engine = get_engine(sync=False)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


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
