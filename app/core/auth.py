from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import get_session
from app.models import User

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    api_key: str = Security(api_key_header), session: AsyncSession = Depends(get_session)
) -> User:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )

    # For MVP of Phase 2, we might not have users inserted yet.
    # We can allow a "dev" backdoor or strictly check DB.
    # Let's strictly check DB but fall back to a mock if DB is empty?
    # No, let's Stick to the plan: Check DB.

    result = await session.execute(select(User).where(User.api_key == api_key))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )

    return user
