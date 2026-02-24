import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import get_current_user
from app.core.db import get_session
from app.core.security import encrypt_secret
from app.models.secret import Secret, SecretScope
from app.models.user import User

router = APIRouter(prefix="/secrets", tags=["Secrets"])
logger = logging.getLogger(__name__)


class SecretCreate(BaseModel):
    key: str
    value: str
    scope: SecretScope = SecretScope.user_scope
    plugin_id: Optional[int] = None


class SecretUpdate(BaseModel):
    value: str


class SecretResponse(BaseModel):
    id: Optional[int]
    key: str
    value: str
    scope: SecretScope
    plugin_id: Optional[int]
    owner_id: Optional[int]


@router.get("/", response_model=List[SecretResponse])
async def list_secrets(session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    """List secrets owned by the current user or global secrets if admin."""
    query = select(Secret)
    if current_user.role == "admin":
        # Admins can see all secrets (or we can just list global + their own)
        pass
    else:
        # Users can only see their own secrets
        query = query.where(Secret.owner_id == current_user.id)

    result = await session.execute(query)
    secrets = result.scalars().all()

    responses = []
    for s in secrets:
        # Mask the value for listing
        responses.append(
            SecretResponse(
                id=s.id, key=s.key, value="********", scope=s.scope, plugin_id=s.plugin_id, owner_id=s.owner_id
            )
        )
    return responses


@router.post("/", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def create_secret(
    secret_in: SecretCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new secret."""
    if secret_in.scope == SecretScope.global_scope and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create global secrets")

    # Encrypt the value
    encrypted_val = encrypt_secret(secret_in.value)

    owner_id = current_user.id if secret_in.scope == SecretScope.user_scope else None

    db_secret = Secret(
        key=secret_in.key,
        encrypted_value=encrypted_val,
        scope=secret_in.scope,
        plugin_id=secret_in.plugin_id,
        owner_id=owner_id,
    )

    session.add(db_secret)
    await session.commit()
    await session.refresh(db_secret)

    return SecretResponse(
        id=db_secret.id,
        key=db_secret.key,
        value="********",
        scope=db_secret.scope,
        plugin_id=db_secret.plugin_id,
        owner_id=db_secret.owner_id,
    )


@router.get("/{secret_id}", response_model=SecretResponse)
async def get_secret(
    secret_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """Get a specific secret by ID."""
    secret = await session.get(Secret, secret_id)
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

    if secret.scope == SecretScope.user_scope and secret.owner_id != current_user.id:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this secret")

    return SecretResponse(
        id=secret.id,
        key=secret.key,
        value="********",
        scope=secret.scope,
        plugin_id=secret.plugin_id,
        owner_id=secret.owner_id,
    )


@router.patch("/{secret_id}", response_model=SecretResponse)
async def update_secret(
    secret_id: int,
    secret_in: SecretUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update a secret's value."""
    secret = await session.get(Secret, secret_id)
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

    if secret.scope == SecretScope.user_scope and secret.owner_id != current_user.id:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this secret")

    if secret.scope == SecretScope.global_scope and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update global secrets")

    secret.encrypted_value = encrypt_secret(secret_in.value)

    session.add(secret)
    await session.commit()
    await session.refresh(secret)

    return SecretResponse(
        id=secret.id,
        key=secret.key,
        value="********",
        scope=secret.scope,
        plugin_id=secret.plugin_id,
        owner_id=secret.owner_id,
    )


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    secret_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """Delete a secret."""
    secret = await session.get(Secret, secret_id)
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

    if secret.scope == SecretScope.user_scope and secret.owner_id != current_user.id:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this secret")

    if secret.scope == SecretScope.global_scope and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete global secrets")

    await session.delete(secret)
    await session.commit()
    return None
