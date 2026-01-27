from langchain_core.tools import tool
from app.core.decorators import require_role

@tool
@require_role("user")
async def save_insight(content: str, user_id: int) -> str:
    """
    Save an important insight or lesson learned to long-term memory.
    Use this when the user shares valuable information, experiences, or lessons that should be remembered.
    
    Args:
        content: The insight or lesson to remember
        user_id: User ID (auto-injected)
    """
    from app.core.memory import memory_manager
    
    await memory_manager.add_memory(
        user_id=user_id,
        content=content,
        memory_type="reflexion"
    )
    return f"✅ Insight saved to memory: {content[:50]}..."

@tool
@require_role("user")
async def store_preference(content: str, user_id: int) -> str:
    """
    Store a user preference or profile information for personalization.
    Use this when the user expresses preferences, habits, or personal information.
    
    Args:
        content: The preference or profile information to store
        user_id: User ID (auto-injected)
    """
    from app.core.memory import memory_manager
    
    await memory_manager.add_memory(
        user_id=user_id,
        content=content,
        memory_type="profile"
    )
    return f"✅ Preference stored: {content[:50]}..."
