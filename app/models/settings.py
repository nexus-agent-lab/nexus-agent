from typing import Optional
from sqlmodel import Field, SQLModel

class SystemSetting(SQLModel, table=True):
    """
    Key-Value store for system configuration.
    """
    key: str = Field(primary_key=True)
    value: str
    description: Optional[str] = None
