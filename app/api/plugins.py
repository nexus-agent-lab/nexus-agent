import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import require_admin
from app.core.db import get_session
from app.models.plugin import Plugin
from app.models.user import User

router = APIRouter(prefix="/plugins", tags=["Plugins"])
logger = logging.getLogger(__name__)


class PluginCreate(BaseModel):
    name: str
    type: str
    source_url: str
    status: str = "active"
    config: dict = {}


class PluginUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    source_url: Optional[str] = None
    status: Optional[str] = None
    config: Optional[dict] = None


@router.get("/", response_model=List[Plugin])
async def list_plugins(session: AsyncSession = Depends(get_session), current_user: User = Depends(require_admin)):
    """List all available plugins."""
    result = await session.execute(select(Plugin))
    return result.scalars().all()


@router.get("/{plugin_id}", response_model=Plugin)
async def get_plugin(
    plugin_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_admin)
):
    """Get a specific plugin by ID."""
    plugin = await session.get(Plugin, plugin_id)
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")
    return plugin


@router.post("/", response_model=Plugin, status_code=status.HTTP_201_CREATED)
async def create_plugin(
    plugin_in: PluginCreate, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_admin)
):
    """Create a new plugin."""
    db_plugin = Plugin(
        name=plugin_in.name,
        type=plugin_in.type,
        source_url=plugin_in.source_url,
        status=plugin_in.status,
        config=plugin_in.config,
    )
    session.add(db_plugin)
    await session.commit()
    await session.refresh(db_plugin)
    return db_plugin


@router.patch("/{plugin_id}", response_model=Plugin)
async def update_plugin(
    plugin_id: int,
    plugin_in: PluginUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Update an existing plugin."""
    plugin = await session.get(Plugin, plugin_id)
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")

    update_data = plugin_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plugin, key, value)

    session.add(plugin)
    await session.commit()
    await session.refresh(plugin)
    return plugin


@router.delete("/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plugin(
    plugin_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_admin)
):
    """Delete a plugin."""
    plugin = await session.get(Plugin, plugin_id)
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")

    await session.delete(plugin)
    await session.commit()
    return None
