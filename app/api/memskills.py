from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import require_admin
from app.core.db import get_session
from app.core.designer import MemSkillDesigner
from app.models.memory_skill import MemorySkill, MemorySkillChangelog

router = APIRouter(prefix="/memskills", tags=["memskills"])


class MemorySkillResponse(BaseModel):
    id: int
    name: str
    description: str
    skill_type: str
    prompt_template: str
    version: int
    is_base: bool
    source_file: Optional[str] = None
    status: str
    positive_count: int
    negative_count: int
    created_at: datetime
    updated_at: datetime


class MemorySkillStatsResponse(BaseModel):
    total_skills: int
    active_skills: int
    canary_skills: int
    deprecated_skills: int
    feedback_data: List[dict]


class MemorySkillChangelogResponse(BaseModel):
    id: int
    skill_id: int
    skill_name: str
    old_prompt: str
    new_prompt: str
    reason: str
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None


@router.get("", response_model=List[MemorySkillResponse], dependencies=[Depends(require_admin)])
async def list_memskills(session: AsyncSession = Depends(get_session)):
    """List all Memory Skills."""
    result = await session.execute(select(MemorySkill).order_by(MemorySkill.name))
    return result.scalars().all()


@router.get("/stats", response_model=MemorySkillStatsResponse, dependencies=[Depends(require_admin)])
async def get_memskills_stats(session: AsyncSession = Depends(get_session)):
    """Get statistics for Memory Skills."""
    skills = (await session.execute(select(MemorySkill))).scalars().all()

    total = len(skills)
    active = sum(1 for s in skills if s.status == "active")
    canary = sum(1 for s in skills if s.status == "canary")
    deprecated = sum(1 for s in skills if s.status == "deprecated")

    feedback_data = [
        {
            "name": s.name,
            "positive_count": s.positive_count,
            "negative_count": s.negative_count
        }
        for s in skills
    ]

    return MemorySkillStatsResponse(
        total_skills=total,
        active_skills=active,
        canary_skills=canary,
        deprecated_skills=deprecated,
        feedback_data=feedback_data
    )


@router.get("/changelogs", response_model=List[MemorySkillChangelogResponse], dependencies=[Depends(require_admin)])
async def list_changelogs(session: AsyncSession = Depends(get_session), limit: int = 20):
    """List recent Memory Skill changelogs."""
    result = await session.execute(
        select(MemorySkillChangelog)
        .order_by(MemorySkillChangelog.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{id}", response_model=MemorySkillResponse, dependencies=[Depends(require_admin)])
async def get_memskill(id: int, session: AsyncSession = Depends(get_session)):
    """Get a specific Memory Skill by ID."""
    skill = await session.get(MemorySkill, id)
    if not skill:
        raise HTTPException(status_code=404, detail="Memory Skill not found")
    return skill


@router.post("/evolve", dependencies=[Depends(require_admin)])
async def evolve_all_memskills():
    """Run the evolution cycle on all underperforming skills."""
    summary = await MemSkillDesigner.run_evolution_cycle()
    return {"message": summary}


@router.post("/{id}/evolve", dependencies=[Depends(require_admin)])
async def evolve_memskill(id: int, session: AsyncSession = Depends(get_session)):
    """Evolve a specific Memory Skill."""
    skill = await session.get(MemorySkill, id)
    if not skill:
        raise HTTPException(status_code=404, detail="Memory Skill not found")

    result = await MemSkillDesigner.evolve_skill(skill)
    if not result:
        raise HTTPException(status_code=500, detail="Evolution failed or no samples available")

    return {"message": "Evolution completed", "result": result}


@router.post("/changelogs/{id}/approve", dependencies=[Depends(require_admin)])
async def approve_changelog(id: int):
    """Approve a canary changelog."""
    result = await MemSkillDesigner.approve_changelog(id)
    if "❌" in result:
        raise HTTPException(status_code=400, detail=result)
    return {"message": result}


@router.post("/changelogs/{id}/reject", dependencies=[Depends(require_admin)])
async def reject_changelog(id: int):
    """Reject a canary changelog."""
    result = await MemSkillDesigner.reject_changelog(id)
    if "❌" in result:
        raise HTTPException(status_code=400, detail=result)
    return {"message": result}

