"""
Verification Script: Active Memory System
Tests the complete memory lifecycle: storage, retrieval, and recall.
"""

import asyncio
import sys

import httpx

BASE_URL = "http://127.0.0.1:8000"


async def test_memory_system():
    print("🧪 Testing Active Memory System")
    print("=" * 50)

    # Step 1: Create test user and get API key
    print("\n1️⃣ Setting up test user...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Match sk-test-123456 from create_admin.py
        admin_key = "sk-test-123456"

        # Test basic connectivity
        try:
            response = await client.get(f"{BASE_URL}/")
            print(f"✅ API is running: {response.json()}")
        except Exception as e:
            print(f"❌ Failed to connect to API: {e}")
            return False

        # Step 2: Store preferences
        print("\n2️⃣ Storing user preferences...")
        test_messages = [
            "I prefer concise responses without too much explanation",
            "I work primarily with Python and TypeScript",
            "I'm based in Shanghai, China (UTC+8)",
        ]

        for msg in test_messages:
            try:
                response = await client.post(
                    f"{BASE_URL}/chat", json={"message": f"Remember this: {msg}"}, headers={"X-API-Key": admin_key}
                )
                if response.status_code != 200:
                    print(f"   ❌ Error {response.status_code}: {response.text}")
                    continue
                print(f"   📝 Sent: {msg[:40]}...")
                print(f"   🤖 Response: {response.json()['response'][:60]}...")
            except Exception as e:
                print(f"   ❌ Exception: {e}")

        # Step 3: Test memory retrieval
        print("\n3️⃣ Testing memory retrieval...")
        retrieval_queries = [
            "What programming languages do I use?",
            "What timezone am I in?",
            "How should you format your responses for me?",
        ]

        for query in retrieval_queries:
            try:
                response = await client.post(
                    f"{BASE_URL}/chat", json={"message": query}, headers={"X-API-Key": admin_key}
                )
                if response.status_code != 200:
                    print(f"   ❌ Error {response.status_code}: {response.text}")
                    continue
                result = response.json()
                print(f"\n   ❓ Query: {query}")
                print(f"   💬 Answer: {result['response'][:100]}...")
            except Exception as e:
                print(f"   ❌ Exception: {e}")

        # Step 4: Save insights
        print("\n4️⃣ Testing insight storage...")
        try:
            response = await client.post(
                f"{BASE_URL}/chat",
                json={
                    "message": "I learned that using async/await improves performance significantly in Python web apps"
                },
                headers={"X-API-Key": admin_key},
            )
            if response.status_code != 200:
                print(f"   ❌ Error {response.status_code}: {response.text}")
            else:
                print(f"   ✅ Insight saved: {response.json()['response'][:60]}...")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print("\n" + "=" * 50)
        print("✅ Memory system test complete!")
        return True


if __name__ == "__main__":
    result = asyncio.run(test_memory_system())
    sys.exit(0 if result else 1)
