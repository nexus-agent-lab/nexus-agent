"""
MemorySkill Model - Intelligent Memory Processing Skills
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Column, Field, SQLModel, Text


class MemorySkill(SQLModel, table=True):
    """
    Memory processing skill for MemSkill system.
    Skills can be 'encoding' (write) or 'retrieval' (read).
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)  # e.g., "fact_extraction"
    description: str  # Human-readable description

    # Skill type: encoding (write) or retrieval (read)
    skill_type: str = Field(index=True)  # "encoding" | "retrieval"

    # The prompt template (Jinja2 format)
    prompt_template: str = Field(sa_column=Column(Text, nullable=False))

    # Version management
    version: int = Field(default=1)
    is_base: bool = Field(default=True)  # False = Designer generated
    source_file: Optional[str] = None  # Original .md file path

    # Safety status for Designer-generated skills
    status: str = Field(default="active")  # "active" | "canary" | "deprecated"

    # Feedback metrics for Designer evaluation
    positive_count: int = Field(default=0)  # Successful usage
    negative_count: int = Field(default=0)  # Failed/corrected usage

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MemorySkillChangelog(SQLModel, table=True):
    """
    Audit log for Designer changes to Memory Skills.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    skill_id: int = Field(foreign_key="memoryskill.id", index=True)
    skill_name: str

    # Change details
    old_prompt: str = Field(sa_column=Column(Text))
    new_prompt: str = Field(sa_column=Column(Text))
    reason: str = Field(sa_column=Column(Text))  # Designer's analysis

    # Review status
    status: str = Field(default="canary")  # "canary" | "approved" | "rejected"

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
