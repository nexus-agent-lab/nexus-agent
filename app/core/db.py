import asyncio
import logging
import os
import secrets

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select

# Basic logging setup
import app.core.logging_config  # noqa: F401  — Centralized logging

logger = logging.getLogger(__name__)

# Import models to register them with SQLModel.metadata

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://nexus:nexus_password@localhost:5432/nexus_db")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    max_retries = 10
    retry_interval = 2

    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                # Ensure pgvector extension exists only on PostgreSQL
                if engine.dialect.name == "postgresql":
                    from sqlalchemy import text

                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

                # await conn.run_sync(SQLModel.metadata.drop_all)
                await conn.run_sync(SQLModel.metadata.create_all)

                # Provision initial admin user if no users exist
                from app.models.user import User

                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(func.count(User.id)))
                    user_count = result.scalar()

                    if user_count == 0:
                        username = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
                        api_key = os.getenv("INITIAL_ADMIN_API_KEY")

                        if not api_key:
                            api_key = secrets.token_urlsafe(16)

                        admin_user = User(username=username, api_key=api_key, role="admin", language="en")

                        session.add(admin_user)
                        await session.commit()

                        # Print visible warning with credentials
                        warning_box = """
┌─────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ╔══════════════════════════════════════════════════════════════╗  │
│  ║                                                                 ║  │
│  ║    ⚠️  INITIAL ADMIN USER CREATED ⚠️                             ║  │
│  ║                                                                 ║  │
│  ║    Username: {username:<50} ║  │
│  ║    API Key:   {api_key:<50} ║  │
│  ║                                                                 ║  │
│  ║    Please save these credentials securely!                     ║  │
│  ║    Use them to log into the Mission Control Dashboard.         ║  │
│  ║                                                                 ║  │
│  ╚══════════════════════════════════════════════════════════════╝  │
│                                                                     │
└─────────────────────────────────────────────────────────────────┘""".format(username=username, api_key=api_key)
                        logger.warning("\n" + warning_box)
            logger.info("Database initialized successfully.")
            return
        except Exception as e:
            logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(retry_interval)

    logger.error("Could not connect to database after maximum retries.")
    raise Exception("Database connection failed")


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
