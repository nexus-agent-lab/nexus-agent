import asyncio
import os
import sys

import requests

# Ensure app module can be found
sys.path.append(os.getcwd())

from sqlalchemy import text

from app.core.db import AsyncSessionLocal

BASE_URL = "http://localhost:8000"


async def get_admin_key():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT api_key FROM \"user\" WHERE username = 'admin'"))
        user = result.first()
        if user:
            return user[0]
        return None


async def test_mcp_custom_tool(api_key):
    """Test calling the custom Python MCP tool as Admin."""
    print("--- Testing Custom MCP Tool (Internal API) ---")

    print(f"Using Admin API Key: {api_key[:5]}...")
    headers = {"X-API-Key": api_key}

    payload = {
        "message": ("Check my internal database for 'Project X' status immediately using the internal API tool.")
    }

    try:
        # Use sync requests for simplicity in this script, as it's separate from async loops
        response = requests.post(f"{BASE_URL}/chat", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        print(f"Status: {response.status_code}")
        print(f"Response: {data['response']}")

        if "SECRET_DATA_123" in data["response"] or "Internal Database Result" in data["response"]:
            print("✅ SUCCESS: Custom MCP tool executed successfully.")
        else:
            print("⚠️  WARNING: Response did not contain expected tool output.")

    except Exception as e:
        print(f"❌ FAIL: {e}")


async def test_mcp_ha_tool(api_key):
    """Test calling the Home Assistant MCP tool."""
    print("\n--- Testing Home Assistant MCP Tool (list_entities) ---")

    headers = {"X-API-Key": api_key}
    payload = {"message": "List some entities from my Home Assistant."}

    try:
        response = requests.post(f"{BASE_URL}/chat", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        print(f"Status: {response.status_code}")
        print(f"Response: {data['response'][:200]}...")

        # Verify tool output hint
        if (
            any(tc["name"] == "list_entities" for tc in data.get("tool_calls", []))
            or "entities" in data["response"].lower()
        ):
            print("✅ SUCCESS: Home Assistant MCP tool executed or mentioned.")
        else:
            print("⚠️  WARNING: No clear indication of HA tool execution.")

    except Exception as e:
        print(f"❌ FAIL: {e}")


async def main():
    api_key = await get_admin_key()
    if not api_key:
        print("❌ FAIL: Admin user not found in DB.")
        return

    await test_mcp_custom_tool(api_key)
    await test_mcp_ha_tool(api_key)


if __name__ == "__main__":
    asyncio.run(main())
