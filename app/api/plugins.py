import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import require_admin
from app.core.db import get_session
from app.core.security import encrypt_secret
from app.core.skill_loader import SkillLoader
from app.models.plugin import Plugin
from app.models.secret import Secret, SecretScope
from app.models.user import User

router = APIRouter(prefix="/plugins", tags=["Plugins"])
logger = logging.getLogger(__name__)


def _load_plugin_catalog() -> List[dict]:
    project_root = Path(__file__).parent.parent.parent
    catalog_path = project_root / "plugin_catalog.json"
    if not catalog_path.exists():
        return []
    with open(catalog_path, "r") as f:
        return json.load(f)


def _get_catalog_entry_for_plugin(plugin: Plugin, catalog: List[dict]) -> Optional[dict]:
    for entry in catalog:
        manifest_match = plugin.manifest_id and entry.get("id") == plugin.manifest_id
        source_match = entry.get("source_url") == plugin.source_url
        if manifest_match or source_match:
            return entry
    return None


def _get_bundled_skills_for_plugin(plugin: Plugin, catalog: List[dict]) -> List[str]:
    entry = _get_catalog_entry_for_plugin(plugin, catalog)
    if entry:
        bundled = entry.get("bundled_skills", []) or []
        return [str(skill) for skill in bundled]
    return []


class PluginCreate(BaseModel):
    name: str
    type: str
    source_url: str
    status: str = "active"
    config: dict = {}
    manifest_id: Optional[str] = None
    required_role: str = "user"
    allowed_groups: List[str] = []
    secrets: Optional[Dict[str, str]] = None

    required_role: str = "user"
    secrets: Optional[Dict[str, str]] = None


class PluginUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    source_url: Optional[str] = None
    status: Optional[str] = None
    config: Optional[dict] = None
    manifest_id: Optional[str] = None
    required_role: Optional[str] = None
    allowed_groups: Optional[List[str]] = None
    secrets: Optional[Dict[str, str]] = None

    secrets: Optional[Dict[str, str]] = None


@router.get("/", response_model=List[Plugin])
async def list_plugins(session: AsyncSession = Depends(get_session), current_user: User = Depends(require_admin)):
    """List all available plugins."""
    result = await session.execute(select(Plugin))
    return result.scalars().all()


@router.get("/catalog")
async def get_plugin_catalog(current_user: User = Depends(require_admin)):
    """Get the predefined plugin catalog (App Store)."""
    try:
        return _load_plugin_catalog()
    except Exception as e:
        logger.error(f"Failed to read plugin catalog: {e}")
        raise HTTPException(status_code=500, detail="Failed to load plugin catalog")


@router.get("/{plugin_id}/schema")
async def get_plugin_schema(
    plugin_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_admin)
):
    """Get the configuration schema for a specific plugin from the catalog."""
    plugin = await session.get(Plugin, plugin_id)
    if not plugin:
        return {"env_schema": None, "bundled_skills": []}

    try:
        catalog = _load_plugin_catalog()
        entry = _get_catalog_entry_for_plugin(plugin, catalog)
        if entry:
            return {"env_schema": entry.get("env_schema"), "bundled_skills": entry.get("bundled_skills", [])}
    except Exception as e:
        logger.error(f"Error reading catalog for schema: {e}")

    return {"env_schema": None, "bundled_skills": []}


@router.get("/{plugin_id}/skill")
async def get_plugin_skill(
    plugin_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(require_admin)
):
    """Get the markdown content of the skill associated with this plugin."""
    plugin = await session.get(Plugin, plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    try:
        catalog = _load_plugin_catalog()
        bundled_skills = _get_bundled_skills_for_plugin(plugin, catalog)
        skill_id = bundled_skills[0] if bundled_skills else None

        if not skill_id:
            raise HTTPException(status_code=404, detail="No bundled skill found for this plugin")

        skill = SkillLoader.load_by_name(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill file '{skill_id}.md' not found")

        # SkillLoader.load_by_name returns a raw string content
        return {"skill_name": skill_id, "content": skill, "metadata": SkillLoader._extract_metadata(skill)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading skill for plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    existing = await session.execute(
        select(Plugin).where((Plugin.name == plugin_in.name) | (Plugin.source_url == plugin_in.source_url))
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A plugin with the name '{plugin_in.name}' or the same source URL already exists.",
        )

    db_plugin = Plugin(
        name=plugin_in.name,
        type=plugin_in.type,
        source_url=plugin_in.source_url,
        status=plugin_in.status,
        config=plugin_in.config,
        manifest_id=plugin_in.manifest_id,
        required_role=plugin_in.required_role,
        allowed_groups=plugin_in.allowed_groups,
    )

    session.add(db_plugin)
    await session.commit()
    await session.refresh(db_plugin)
    if plugin_in.secrets:
        for key, value in plugin_in.secrets.items():
            encrypted_val = encrypt_secret(value)
            secret_db = Secret(
                key=key,
                encrypted_value=encrypted_val,
                scope=SecretScope.global_scope,
                plugin_id=db_plugin.id,
                owner_id=None,
            )
            session.add(secret_db)
        await session.commit()

    try:
        catalog = _load_plugin_catalog()
        bundled_skills = _get_bundled_skills_for_plugin(db_plugin, catalog)
        for skill in bundled_skills:
            await SkillLoader.install_skill(skill)
        if bundled_skills:
            await SkillLoader.refresh_runtime_skill_registry(role="admin")
    except Exception as e:
        logger.error(f"Failed to process bundled skills: {e}")

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
    secrets_to_update = update_data.pop("secrets", None)

    for key, value in update_data.items():
        setattr(plugin, key, value)

    session.add(plugin)

    if secrets_to_update:
        for key, value in secrets_to_update.items():
            if not value:
                continue

            encrypted_val = encrypt_secret(value)

            # Upsert logic for secrets
            from sqlmodel import and_

            existing_secret_result = await session.execute(
                select(Secret).where(and_(Secret.plugin_id == plugin.id, Secret.key == key))
            )
            existing_secret = existing_secret_result.scalars().first()

            if existing_secret:
                existing_secret.encrypted_value = encrypted_val
                session.add(existing_secret)
            else:
                new_secret = Secret(
                    key=key,
                    encrypted_value=encrypted_val,
                    scope=SecretScope.global_scope,
                    plugin_id=plugin.id,
                    owner_id=None,
                )
                session.add(new_secret)

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

    catalog = _load_plugin_catalog()
    bundled_skills = _get_bundled_skills_for_plugin(plugin, catalog)

    other_plugins_result = await session.execute(select(Plugin).where(Plugin.id != plugin.id))
    other_plugins = list(other_plugins_result.scalars().all())
    skills_still_referenced = set()
    for other in other_plugins:
        skills_still_referenced.update(_get_bundled_skills_for_plugin(other, catalog))

    await session.delete(plugin)
    await session.commit()

    removed_any_skill = False
    for skill_name in bundled_skills:
        if skill_name in skills_still_referenced:
            continue
        if SkillLoader.delete_skill(skill_name):
            removed_any_skill = True

    if removed_any_skill or bundled_skills:
        await SkillLoader.refresh_runtime_skill_registry(role="admin")

    return None
