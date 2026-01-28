"""
Skill API endpoints for managing and generating skill cards.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.skill_generator import SkillGenerator
from app.core.skill_loader import SkillLoader
from app.models.user import User

router = APIRouter(prefix="/skills", tags=["skills"])


class SkillInfo(BaseModel):
    """Skill metadata."""

    name: str
    file: str
    domain: str
    priority: str


class SkillContent(BaseModel):
    """Full skill card content."""

    name: str
    content: str


class GenerateSkillRequest(BaseModel):
    """Request to generate a new skill card."""

    mcp_name: str
    tools: List[dict]
    domain: str = "unknown"


class GenerateSkillResponse(BaseModel):
    """Response from skill generation."""

    name: str
    content: str
    success: bool
    message: str


@router.get("/", response_model=List[SkillInfo])
async def list_skills(current_user: User = Depends(get_current_user)):
    """List all available skill cards."""
    skills = SkillLoader.list_skills()
    return skills


@router.get("/{skill_name}", response_model=SkillContent)
async def get_skill(skill_name: str, current_user: User = Depends(get_current_user)):
    """Get a specific skill card content."""
    content = SkillLoader.load_by_name(skill_name)

    if content is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    return SkillContent(name=skill_name, content=content)


@router.post("/generate", response_model=GenerateSkillResponse)
async def generate_skill(request: GenerateSkillRequest, current_user: User = Depends(get_current_user)):
    """
    Generate a new skill card using AI.

    Requires admin role for safety.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to generate skills")

    try:
        # Generate skill card
        content = await SkillGenerator.generate_skill_card(
            mcp_name=request.mcp_name, tools=request.tools, domain=request.domain
        )

        return GenerateSkillResponse(
            name=request.mcp_name, content=content, success=True, message="Skill card generated successfully"
        )
    except Exception as e:
        return GenerateSkillResponse(
            name=request.mcp_name, content="", success=False, message=f"Failed to generate skill: {str(e)}"
        )


@router.put("/{skill_name}")
async def save_skill(skill_name: str, content: str, current_user: User = Depends(get_current_user)):
    """
    Save or update a skill card.

    Requires admin role for safety.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to save skills")

    success = SkillLoader.save_skill(skill_name, content)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save skill card")

    return {"message": f"Skill '{skill_name}' saved successfully"}


@router.delete("/{skill_name}")
async def delete_skill(skill_name: str, current_user: User = Depends(get_current_user)):
    """
    Delete a skill card.

    Requires admin role for safety.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to delete skills")

    skill_file = SkillLoader.SKILLS_DIR / f"{skill_name}.md"

    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    try:
        skill_file.unlink()
        return {"message": f"Skill '{skill_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete skill: {str(e)}")
