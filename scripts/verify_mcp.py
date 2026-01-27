import requests
import json
import asyncio
import sys
import os

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

def test_mcp_custom_tool():
    """Test calling the custom Python MCP tool as Admin."""
    print("--- Testing Custom MCP Tool (Internal API) ---")
    
    # 1. Login/Check Admin
    api_key = asyncio.run(get_admin_key())
    if not api_key:
        print("❌ FAIL: Admin user not found in DB.")
        return

    print(f"Using Admin API Key: {api_key[:5]}...")
    headers = {"X-API-Key": api_key}
    
    # 2. Send Chat Request
    # The tool name comes from `servers/demo_tool.py` -> `internal_api_tool`
    # The prompt should trigger it.
    payload = {
        "message": "I am the system administrator. Query the internal database for 'Project X' status immediately using the internal API tool."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Response: {data['response']}")
        print(f"Tool Calls: {data.get('tool_calls', '[]')}")
        
        # Verify tool output was used
        if "SECRET_DATA_123" in data['response'] or "Internal Database Result" in data['response']:
             print("✅ SUCCESS: Custom MCP tool executed successfully.")
        else:
             print("⚠️  WARNING: Response did not contain expected tool output. Check logs.")
             
    except Exception as e:
        print(f"❌ FAIL: {e}")
        if 'response' in locals():
            print(response.text)

if __name__ == "__main__":
    test_mcp_custom_tool()
