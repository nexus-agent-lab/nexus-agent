import os
from datetime import datetime, timedelta
import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import get_current_user
from app.core.auth_service import AuthService
from app.core.db import get_session
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-default-key-1234")
ALGORITHM = "HS256"


@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)
):
    """
    OAuth2 compatible token login, returning a JWT token.
    For MVP, password field expects the user's API key.
    """
    result = await session.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()

    if not user or user.api_key != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(hours=24)
    expire = datetime.utcnow() + access_token_expires
    to_encode = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "api_key": user.api_key,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.info(f"JWT token issued for user: {user.username} (ID: {user.id})")

    return {
        "access_token": encoded_jwt,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }


class BindTokenResponse(BaseModel):
    token: str
    expires_in: int = 300


@router.post("/bind-token", response_model=BindTokenResponse)
async def generate_bind_token(current_user: User = Depends(get_current_user)):
    """
    Generate a temporary 6-digit token to link a 3rd party account (Telegram/Feishu).
    """
    token = await AuthService.create_bind_token(current_user.id)
    return BindTokenResponse(token=token)
