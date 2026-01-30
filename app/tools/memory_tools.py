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

    await memory_manager.add_memory(user_id=user_id, content=content, memory_type="reflexion")
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

    await memory_manager.add_memory(user_id=user_id, content=content, memory_type="profile")
    return f"✅ Preference stored: {content[:50]}..."


@tool
@require_role("user")
async def query_memory(query: str = None, memory_type: str = None, user_id: int = None) -> str:
    """
    Search or list your long-term memories, preferences, and saved insights.
    If 'query' is provided, it performs a semantic search.
    If only 'memory_type' is provided, it lists the most recent memories of that type.

    Args:
        query: Optional search term. Use this to find specific information.
        memory_type: Optional type filter ('profile', 'reflexion', 'knowledge').
        user_id: User ID (auto-injected)
    """
    from app.core.memory import memory_manager

    if query:
        memories = await memory_manager.search_memory(user_id=user_id, query=query)
        if not memories:
            return f"❓ No memories found matching: {query}"
        
        results = [f"ID:{m.id} [{m.memory_type}] {m.content}" for m in memories]
        return "🧠 **Found the following memories:**\n\n" + "\n".join(results)
    
    # List by type if no query
    memories = await memory_manager.list_memories(user_id=user_id, memory_type=memory_type)
    if not memories:
        type_str = f" of type '{memory_type}'" if memory_type else ""
        return f"❓ No memories found{type_str}."

    results = [f"ID:{m.id} [{m.memory_type}] {m.content}" for m in memories]
    return f"🧠 **Your recent memories{'' if not memory_type else ' (' + memory_type + ')'}:**\n\n" + "\n".join(results)


@tool
@require_role("user")
async def forget_memory(memory_id: int, user_id: int = None) -> str:
    """
    Delete a specific piece of information from your memory.
    Use this when the user corrects you, or when you realize information is outdated or incorrect.

    Args:
        memory_id: The ID of the memory to delete (find this using query_memory).
        user_id: User ID (auto-injected)
    """
    from app.core.memory import memory_manager

    success = await memory_manager.delete_memory(user_id=user_id, memory_id=memory_id)
    if success:
        return f"✅ Memory ID:{memory_id} has been forgotten."
    return f"❌ Failed to find memory with ID:{memory_id}."
