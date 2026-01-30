import asyncio
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# Basic logging setup
logging.basicConfig(level=logging.INFO)
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
                # await conn.run_sync(SQLModel.metadata.drop_all)
                await conn.run_sync(SQLModel.metadata.create_all)
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
