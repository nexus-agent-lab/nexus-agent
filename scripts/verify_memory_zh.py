"""
Verification Script: Active Memory System (Chinese)
专门测试 bge-small-zh 模型在中文环境下的记忆表现。
"""

import asyncio
import sys

import httpx

BASE_URL = "http://127.0.0.1:8000"


async def test_memory_system_zh():
    print("🧪 测试主动记忆系统 (中文优化)")
    print("=" * 50)

    # Step 1: 环境准备
    print("\n1️⃣ 设置测试用户...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        admin_key = "sk-test-123456"

        try:
            response = await client.get(f"{BASE_URL}/")
            print(f"✅ API 运行中: {response.json()}")
        except Exception as e:
            print(f"❌ 无法连接到 API: {e}")
            return False

        # Step 2: 存储中文偏好
        print("\n2️⃣ 存储用户偏好 (中文)...")
        test_messages = [
            "我非常喜欢用 Python 编写后端逻辑，前端则偏好使用 Tailwind CSS",
            "我目前居住在上海，平时沟通主要使用中文",
            "我希望我的助手的回答风格是专业且简洁的",
        ]

        for msg in test_messages:
            try:
                response = await client.post(
                    f"{BASE_URL}/chat", json={"message": f"请记住这个信息: {msg}"}, headers={"X-API-Key": admin_key}
                )
                if response.status_code != 200:
                    print(f"   ❌ 错误 {response.status_code}: {response.text}")
                    continue
                print(f"   📝 已发送: {msg[:30]}...")
                print(f"   🤖 响应: {response.json()['response'][:50]}...")
            except Exception as e:
                print(f"   ❌ 异常: {e}")

        # Step 3: 测试中文记忆检索
        print("\n3️⃣ 测试记忆检索 (中文语义匹配)...")
        retrieval_queries = ["我后端和前端分别喜欢用什么技术栈？", "我住在哪个城市？", "我对助手回复的风格有什么要求？"]

        for query in retrieval_queries:
            try:
                response = await client.post(
                    f"{BASE_URL}/chat", json={"message": query}, headers={"X-API-Key": admin_key}
                )
                if response.status_code != 200:
                    print(f"   ❌ 错误 {response.status_code}: {response.text}")
                    continue
                result = response.json()
                print(f"\n   ❓ 提问: {query}")
                print(f"   💬 助手回答: {result['response'][:100]}...")
            except Exception as e:
                print(f"   ❌ 异常: {e}")

        # Step 4: 存储经验总结 (Reflexion)
        print("\n4️⃣ 测试经验总结存储...")
        try:
            response = await client.post(
                f"{BASE_URL}/chat",
                json={"message": "我发现对于本地部署的智能体，使用 uv 管理依赖比传统的 pip 快得多"},
                headers={"X-API-Key": admin_key},
            )
            if response.status_code != 200:
                print(f"   ❌ 错误 {response.status_code}: {response.text}")
            else:
                print(f"   ✅ 经验已保存: {response.json()['response'][:60]}...")
        except Exception as e:
            print(f"   ❌ 异常: {e}")

        print("\n" + "=" * 50)
        print("✅ 中文记忆系统测试完成！")
        return True


if __name__ == "__main__":
    result = asyncio.run(test_memory_system_zh())
    sys.exit(0 if result else 1)
