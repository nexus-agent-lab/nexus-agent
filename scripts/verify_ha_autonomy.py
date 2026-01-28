import asyncio
import logging
import os
import sys

# Enhance path to allow imports from app
sys.path.append("/app")
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage
from sqlalchemy import text

from app.core.agent import create_agent_graph
from app.core.db import AsyncSessionLocal
from app.core.mcp_manager import get_mcp_tools
from app.core.state import AgentState
from app.models.user import User

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_ha")


async def get_admin_user():
    """Fetch the real admin user from DB to satisfy FK constraints"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT * FROM \"user\" WHERE role = 'admin' LIMIT 1"))
        user_row = result.first()
        if user_row:
            # Reconstruct User object (assuming order based on model)
            return User(id=user_row.id, username=user_row.username, api_key=user_row.api_key, role=user_row.role)
        return None


async def run_test():
    print("--- 🧪 Starting HA Autonomy Debug ---")

    # 1. Load Tools (MCP + System)
    print("Loading tools...")
    try:
        from app.tools.registry import get_static_tools

        mcp_tools = await get_mcp_tools()
        system_tools = get_static_tools()  # Includes python_sandbox

        tools = mcp_tools + system_tools
        print(f"Loaded {len(tools)} tools: {[t.name for t in tools]}")
    except Exception as e:
        print(f"Failed to load tools: {e}")
        import traceback

        traceback.print_exc()
        return

    # 2. Create Graph
    print("Creating Agent Graph...")
    app = create_agent_graph(tools)

    # 3. Test Query
    # Scenario: User asks for temp, ID is unknown. Agent MUST search.
    query = "给我查一下客厅温度。"
    print(f"\n📝 User Query: {query}")

    # Fetch real admin user
    admin_user = await get_admin_user()
    if not admin_user:
        print("❌ FAIL: No admin user found in DB. Run create_admin.py first.")
        return

    print(f"Authenticated as: {admin_user.username} (Role: {admin_user.role})")

    initial_state = AgentState(messages=[HumanMessage(content=query)], user=admin_user, files=[], context="home")

    print("\n--- 🏃 Running Graph ---")
    async for event in app.astream(initial_state):
        for node, values in event.items():
            print(f"\n[Node: {node}]")
            if "messages" in values:
                last_msg = values["messages"][-1]
                print(f"Type: {last_msg.type}")
                print(f"Content: {last_msg.content}")
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    print(f"Tool Calls: {last_msg.tool_calls}")


if __name__ == "__main__":
    asyncio.run(run_test())
