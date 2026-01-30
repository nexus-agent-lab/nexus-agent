
import asyncio
import os
import sys
from unittest.mock import MagicMock

# Ensure we can import app
sys.path.append(os.getcwd())

from app.core.memory import memory_manager
from app.tools.memory_tools import forget_memory, query_memory, store_preference, save_insight

async def test_memory_flow():
    user_id = 5
    print(f"--- Testing Memory Flow for User {user_id} ---")

    # 1. Store preferences and insights
    print("\n1. Storing memories...")
    await store_preference.ainvoke({"content": "I love drinking espresso in the morning", "user_id": user_id})
    await store_preference.ainvoke({"content": "I prefer dark mode for all my apps", "user_id": user_id})
    await save_insight.ainvoke({"content": "Users feel more productive when the interface is snappy", "user_id": user_id})

    # 2. Test semantic query
    print("\n2. Testing semantic search (query_memory with query)...")
    result_search = await query_memory.ainvoke({"query": "What do I like to drink?", "user_id": user_id})
    print(f"Search Result:\n{result_search}")
    
    # 3. Test list by type
    print("\n3. Testing list by type (query_memory with memory_type)...")
    result_list = await query_memory.ainvoke({"memory_type": "profile", "user_id": user_id})
    print(f"List Result (profile):\n{result_list}")

    # 4. Test list all (no query, no type)
    print("\n4. Testing list all (query_memory with no params)...")
    result_all = await query_memory.ainvoke({"user_id": user_id})
    print(f"List Result (all):\n{result_all}")

    # 5. Test Forget Memory
    print("\n5. Testing forget_memory...")
    # Get ID from result_all (regexp extract or just use first one)
    import re
    match = re.search(r"ID:(\d+)", result_all)
    if match:
        mid = int(match.group(1))
        print(f"Forgetting memory ID: {mid}")
        forget_result = await forget_memory.ainvoke({"memory_id": mid, "user_id": user_id})
        print(f"Forget Result: {forget_result}")
        
        # Verify it's gone
        verify_gone = await query_memory.ainvoke({"user_id": user_id})
        if f"ID:{mid}" not in verify_gone:
            print("✅ Verified: Memory is gone from listing.")
        else:
            print("❌ Error: Memory still exists in listing!")
    else:
        print("❌ Error: Could not find memory ID in output!")

    print("\n--- Memory Flow Test Completed ---")

if __name__ == "__main__":
    # Check if DB is available (simple check)
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://nexus:nexus_pass@localhost:5432/nexus_db"
    
    try:
        asyncio.run(test_memory_flow())
    except Exception as e:
        print(f"❌ Test failed: {e}")
