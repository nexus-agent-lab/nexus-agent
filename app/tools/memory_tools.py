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

    # Use 'fact_extraction' skill or auto-select
    await memory_manager.add_memory_with_skill(
        user_id=user_id,
        content=content,
        memory_type="reflexion",
        skill_name="fact_extraction"
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

    # Use 'preference_capture' skill
    await memory_manager.add_memory_with_skill(
        user_id=user_id,
        content=content,
        memory_type="profile",
        skill_name="preference_capture"
    )
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

    # Record negative feedback on the originating skill before deletion
    try:
        from sqlmodel import select

        from app.core.db import AsyncSessionLocal
        from app.core.designer import MemSkillDesigner
        from app.models.memory import Memory

        async with AsyncSessionLocal() as session:
            stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()
            if memory and memory.skill_id:
                await MemSkillDesigner.record_feedback(memory.skill_id, is_positive=False)
    except Exception:
        pass  # Non-critical, don't block deletion

    success = await memory_manager.delete_memory(user_id=user_id, memory_id=memory_id)
    if success:
        return f"✅ Memory ID:{memory_id} has been forgotten."
    return f"❌ Failed to find memory with ID:{memory_id}."


@tool
@require_role("user")
async def forget_all_memories(memory_type: str = None, confirm: bool = False, user_id: int = None) -> str:
    """
    Delete MULTIPLE memories at once based on type.
    Use this when the user wants to clear their history, profile, or restart.

    Args:
        memory_type: Optional. The type of memory to delete ('profile', 'reflexion', 'knowledge').
                     If not provided, it deletes ALL memories.
        confirm: You must set this to True to execute the deletion.
        user_id: User ID (auto-injected)
    """
    if not confirm:
        return "❌ Safety Check: You must set 'confirm=True' to bulk delete memories."

    from app.core.memory import memory_manager

    count = await memory_manager.delete_all_memories(user_id=user_id, memory_type=memory_type)

    type_msg = f"of type '{memory_type}' " if memory_type else ""
    return f"✅ forgotten {count} memories {type_msg}for user."


@tool
@require_role("admin")
async def evolve_memory_skills(user_id: int = None) -> str:
    """
    [Admin] Trigger the MemSkill Designer to analyze underperforming memory skills
    and generate improved prompts. Results are saved as canary versions for review.

    Args:
        user_id: User ID (auto-injected)
    """
    from app.core.designer import MemSkillDesigner

    return await MemSkillDesigner.run_evolution_cycle()


@tool
@require_role("admin")
async def list_skill_changelog(limit: int = 10, user_id: int = None) -> str:
    """
    [Admin] View the evolution history of memory skills.
    Shows recent Designer changes with their approval status.

    Args:
        limit: Number of recent entries to show (default: 10)
        user_id: User ID (auto-injected)
    """
    from app.core.designer import MemSkillDesigner

    entries = await MemSkillDesigner.get_changelog_list(limit=limit)
    if not entries:
        return "📋 No evolution history yet."

    lines = ["📋 **Memory Skill Evolution History:**\n"]
    for e in entries:
        status_icon = {"canary": "🟡", "approved": "✅", "rejected": "🚫"}.get(e["status"], "❓")
        lines.append(
            f"{status_icon} **#{e['id']}** [{e['skill_name']}] — {e['status']}\n"
            f"  Reason: {e['reason']}\n"
            f"  Created: {e['created_at']}"
        )
    return "\n".join(lines)


@tool
@require_role("admin")
async def approve_skill_evolution(changelog_id: int, action: str = "approve", user_id: int = None) -> str:
    """
    [Admin] Approve or reject a canary skill evolution.
    Approved changes update the skill's prompt template to the new version.

    Args:
        changelog_id: The changelog entry ID to act on
        action: 'approve' or 'reject'
        user_id: User ID (auto-injected)
    """
    from app.core.designer import MemSkillDesigner

    if action == "approve":
        return await MemSkillDesigner.approve_changelog(changelog_id)
    elif action == "reject":
        return await MemSkillDesigner.reject_changelog(changelog_id)
    else:
        return f"❌ Invalid action: '{action}'. Use 'approve' or 'reject'."
