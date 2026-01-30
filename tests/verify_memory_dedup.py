import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.core.memory import memory_manager

# Mock user id
USER_ID = 9999


async def verify_dedup():
    print("--- Verifying Memory Deduplication ---")

    # Clean up previous test data

    # 0. Clean up previous test data
    from sqlmodel import select

    from app.core.db import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as session:
        user = await session.get(User, USER_ID)
        if user:
            # Manually delete memories first if cascade isn't set up
            # But normally user deletion should cascade if configured, or we delete manual
            from app.models.memory import Memory

            stmt = select(Memory).where(Memory.user_id == USER_ID)
            res = await session.execute(stmt)
            for m in res.scalars():
                await session.delete(m)

            await session.delete(user)
            await session.commit()
            print("🧹 Cleaned up previous test user and memories.")

    # 1. Create User
    async with AsyncSessionLocal() as session:
        user = User(id=USER_ID, username="test_dedup_user", role="user", api_key="test_key_9999")
        session.add(user)
        await session.commit()

    # 1. Add Base Memory
    content1 = "I really love drinking dark roast coffee in the morning."
    print(f"\n1. Adding Base Memory: '{content1}'")
    mem1 = await memory_manager.add_memory(USER_ID, content1)
    print(f"✅ Created Memory ID: {mem1.id}")

    # 2. Add EXACT Duplicate (should be deduped)
    print(f"\n2. Adding Duplicate: '{content1}'")
    mem2 = await memory_manager.add_memory(USER_ID, content1)
    if mem2.id == mem1.id:
        print(f"✅ Deduplication Success! Returned existing ID: {mem2.id}")
    else:
        print(f"❌ Deduplication FAILED! Created new ID: {mem2.id}")

    # 3. Add SEMANTIC Duplicate (should be deduped)
    content3 = "I enjoy having dark roast coffee every morning."
    print(f"\n3. Adding Semantic Duplicate: '{content3}'")
    mem3 = await memory_manager.add_memory(USER_ID, content3)

    if mem3.id == mem1.id:
        print(f"✅ Semantic Deduplication Success! Returned existing ID: {mem3.id}")
    else:
        print(
            f"❌ Semantic Deduplication FAILED! Created new ID: {mem3.id} (This might be expected if similarity < 0.92)"
        )

    # 4. Add DISTINCT Memory (should create new)
    content4 = "I also like tea."
    print(f"\n4. Adding New Memory: '{content4}'")
    mem4 = await memory_manager.add_memory(USER_ID, content4)
    if mem4.id != mem1.id:
        print(f"✅ Distinct Memory Success! Created new ID: {mem4.id}")
    else:
        print("❌ Error: Distinct memory returned old ID!")

    # Cleanup
    print("\n--- Cleanup ---")


if __name__ == "__main__":
    asyncio.run(verify_dedup())
