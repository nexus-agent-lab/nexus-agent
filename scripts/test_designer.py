import asyncio
import os
import sys

# Add app to path
sys.path.append(os.getcwd())

from app.core.db import AsyncSessionLocal
from app.core.designer import MemSkillDesigner
from app.models.memory_skill import MemorySkill


async def setup_dummy_skill():
    """Create a dummy skill with bad performance stats."""
    async with AsyncSessionLocal() as session:
        skill = MemorySkill(
            name="test_evolution_skill",
            skill_type="extraction",
            description="A test skill designed to fail.",
            prompt_template="Extract facts: {{ content }}",
            positive_count=2,
            negative_count=8,  # 80% failure rate
            status="active",
            is_base=False,
        )
        session.add(skill)
        await session.commit()
        await session.refresh(skill)
        print(f"Created dummy skill: {skill.name} (id={skill.id})")
        return skill.id


async def cleanup(skill_id):
    async with AsyncSessionLocal() as session:
        skill = await session.get(MemorySkill, skill_id)
        if skill:
            await session.delete(skill)
            await session.commit()
            print(f"Cleaned up skill {skill_id}")


async def main():
    print("🚀 Starting Designer Test...")

    # Lower constraints for testing
    MemSkillDesigner.MIN_TOTAL_USES = 1
    MemSkillDesigner.NEGATIVE_RATE_THRESHOLD = 0.1

    # 1. Setup Data
    skill_id = await setup_dummy_skill()

    # 2. Run Evolution
    print("\n🧬 Running Evolution Cycle...")
    try:
        summary = await MemSkillDesigner.run_evolution_cycle()
        print("\n✅ Result Summary:")
        print(summary)
    except Exception as e:
        print(f"\n❌ Evolution Failed: {e}")
        import traceback

        traceback.print_exc()

    # 3. Cleanup
    await cleanup(skill_id)


if __name__ == "__main__":
    if os.getenv("LLM_API_KEY") is None:
        print("❌ Error: LLM_API_KEY not set. Run with env vars.")
        sys.exit(1)

    asyncio.run(main())
