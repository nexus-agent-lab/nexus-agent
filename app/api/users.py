import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import get_current_user, require_admin
from app.core.db import get_session
from app.models.user import User, UserIdentity

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)


class UserCreate(BaseModel):
    username: str
    api_key: Optional[str] = None
    role: str = "user"
    language: str = "en"
    timezone: Optional[str] = None
    notes: Optional[str] = None
    policy: Dict[str, Any] = {}


class UserUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    notes: Optional[str] = None
    policy: Optional[Dict[str, Any]] = None


class IdentityBindingCreate(BaseModel):
    provider: str
    provider_user_id: str
    provider_username: Optional[str] = None


@router.get("/", response_model=List[User])
async def list_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """List all users (Admin only)."""
    result = await session.execute(select(User))
    return result.scalars().all()


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a specific user."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user",
        )

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Create a new user (Admin only)."""
    api_key = user_in.api_key or f"sk_{uuid.uuid4().hex}"

    db_user = User(
        username=user_in.username,
        api_key=api_key,
        role=user_in.role,
        language=user_in.language,
        timezone=user_in.timezone,
        notes=user_in.notes,
        policy=user_in.policy,
    )
    session.add(db_user)
    try:
        await session.commit()
        await session.refresh(db_user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or API Key already exists",
        )
    return db_user


@router.patch("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update an existing user."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this user",
        )

    # Standard users cannot change their own role to admin or modify their policy
    if current_user.role != "admin":
        if user_in.role is not None and user_in.role != current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to change role",
            )
        if user_in.policy is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to change policy",
            )

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict in unique fields (e.g. username)",
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Delete a user (Admin only). Standard users cannot delete others or themselves."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await session.delete(user)
    await session.commit()
    return None


@router.get("/{user_id}/bindings", response_model=List[UserIdentity])
async def list_user_bindings(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List identities bound to a user."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these bindings",
        )

    result = await session.execute(select(UserIdentity).where(UserIdentity.user_id == user_id))
    return result.scalars().all()


@router.post("/{user_id}/bindings", response_model=UserIdentity, status_code=status.HTTP_201_CREATED)
async def create_user_binding(
    user_id: int,
    binding_in: IdentityBindingCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new identity binding for a user."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add bindings for this user",
        )

    # Validate that user exists
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check for existing binding across any user
    result = await session.execute(
        select(UserIdentity).where(
            UserIdentity.provider == binding_in.provider,
            UserIdentity.provider_user_id == binding_in.provider_user_id,
        )
    )
    existing_binding = result.scalars().first()
    if existing_binding:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identity already bound to a user",
        )

    db_binding = UserIdentity(
        user_id=user_id,
        provider=binding_in.provider,
        provider_user_id=binding_in.provider_user_id,
        provider_username=binding_in.provider_username,
    )
    session.add(db_binding)
    try:
        await session.commit()
        await session.refresh(db_binding)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create binding",
        )
    return db_binding
