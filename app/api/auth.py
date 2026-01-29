from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.auth_service import AuthService
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


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
