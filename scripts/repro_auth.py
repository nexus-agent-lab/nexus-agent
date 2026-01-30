import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.auth_service import AuthService
from app.core.db import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("repro_auth")


async def main():
    await init_db()

    provider = "telegram"
    user_id = "999888777"

    logger.info(f"Testing lookup for {provider}:{user_id}")

    user = await AuthService.get_user_by_identity(provider, user_id)

    if user:
        logger.info(f"✅ Found User: ID={user.id}, Username={user.username}, Role={user.role}")
    else:
        logger.error("❌ User NOT found!")


if __name__ == "__main__":
    asyncio.run(main())
