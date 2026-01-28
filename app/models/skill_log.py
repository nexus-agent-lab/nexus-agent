from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class SkillChangelog(SQLModel, table=True):
    """
    Audit log for Self-Learning System changes to Skill Cards.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    skill_name: str
    rule_content: str  # The rule text being added
    reason: str        # Error message or context triggering the learn
    
    status: str        # "pending", "approved", "rejected", "auto_applied"
    mode: str          # "auto" or "manual" (snapshot of config at time)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    
    # Metadata
    session_id: Optional[int] = None # Link to session where error occurred
