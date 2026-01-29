from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.models.skill_log import SkillChangelog
from app.models.settings import SystemSetting
from app.core.skill_loader import SkillLoader

router = APIRouter(prefix="/skill-learning", tags=["skill-learning"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/logs", response_model=List[SkillChangelog])
async def list_logs(
    limit: int = 50, 
    offset: int = 0, 
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(SkillChangelog).offset(offset).limit(limit).order_by(SkillChangelog.created_at.desc())
    if status is not None:
        query = query.where(SkillChangelog.status == status)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/logs/{log_id}/approve")
async def approve_log(log_id: int, db: AsyncSession = Depends(get_db)):
    log = await db.get(SkillChangelog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    if log.status != "pending":
        raise HTTPException(status_code=400, detail=f"Log status is {log.status}, cannot approve")

    # Apply the rule
    success = SkillLoader.append_learned_rule(log.skill_name, log.rule_content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write rule to skill card")

    log.status = "approved"
    log.reviewed_at = datetime.utcnow()
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log

@router.post("/logs/{log_id}/reject")
async def reject_log(log_id: int, db: AsyncSession = Depends(get_db)):
    log = await db.get(SkillChangelog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    log.status = "rejected"
    log.reviewed_at = datetime.utcnow()
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log

@router.get("/config/mode")
async def get_learning_mode(db: AsyncSession = Depends(get_db)):
    setting = await db.get(SystemSetting, "SKILL_LEARNING_MODE")
    return {"mode": setting.value if setting else "manual"}

@router.post("/config/mode")
async def set_learning_mode(mode: str, db: AsyncSession = Depends(get_db)):
    if mode not in ["auto", "manual"]:
        raise HTTPException(status_code=400, detail="Mode must be 'auto' or 'manual'")
    
    setting = await db.get(SystemSetting, "SKILL_LEARNING_MODE")
    if not setting:
        setting = SystemSetting(key="SKILL_LEARNING_MODE", value=mode)
    else:
        setting.value = mode
        
    db.add(setting)
    await db.commit()
    return {"mode": mode}
