import asyncio
import logging

from sqlalchemy import text

from app.core.db import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")


async def migrate():
    logger.info("Starting Identity System Migration...")

    # 1. Add columns to 'users' table
    # We must run each DDL in its own transaction block or handle exceptions carefully

    # Check/Add 'role'
    try:
        async with engine.begin() as conn:
            logger.info("Attempting to add 'role' column...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
    except Exception as e:
        logger.info(f"Skipping 'role' column (likely exists): {e}")

    # Check/Add 'policy'
    try:
        async with engine.begin() as conn:
            logger.info("Attempting to add 'policy' column...")
            # Using JSONB for Postgres if possible, else JSON
            await conn.execute(text("ALTER TABLE users ADD COLUMN policy JSONB DEFAULT '{}'"))
    except Exception as e:
        logger.info(f"Skipping 'policy' column (likely exists): {e}")

    # 2. Create 'user_identities' table
    from app.models.user import SQLModel

    async with engine.begin() as conn:
        logger.info("Creating missing tables (UserIdentity)...")
        await conn.run_sync(SQLModel.metadata.create_all)

    logger.info("Migration Complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
