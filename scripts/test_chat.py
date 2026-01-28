import asyncio
import logging
import os
import sys

# We need the app in the path
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage  # noqa: E402

from app.core.agent import create_agent_graph  # noqa: E402
from app.core.mcp_manager import get_mcp_tools  # noqa: E402
from app.models.user import User  # noqa: E402
from app.tools.registry import get_static_tools  # noqa: E402


def test_chat(_query):
    # url = "http://localhost:8000/chat"
    # headers = {"X-API-Key": "nexus_admin_key"}
    pass


# Enable HTTP logging to see Payload & URL
logging.basicConfig(level=logging.WARN)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.DEBUG)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_chat.py 'Your question'")
        sys.exit(1)

    print(f"--- Testing Query: '{sys.argv[1]}' ---")

    # Check Env
    print(f"[Debug] LLM_BASE_URL: {os.getenv('LLM_BASE_URL', 'Not Set')}")
    print(f"[Debug] LLM_MODEL: {os.getenv('LLM_MODEL', 'Not Set')}")

    # Setup Tools
    static_tools = get_static_tools()
    try:
        mcp_tools = await get_mcp_tools()
    except Exception as e:
        print(f"Warning: Failed to load MCP tools: {e}")
        mcp_tools = []

    all_tools = static_tools + mcp_tools
    print(f"Loaded {len(all_tools)} tools.")

    # Create Graph
    graph = create_agent_graph(all_tools)

    # Mock User
    mock_user = User(id=1, username="tester", role="admin")

    # Invoke
    initial_state = {"messages": [HumanMessage(content=sys.argv[1])], "user": mock_user}

    print("Invoking Agent...")
    final_state = await graph.ainvoke(initial_state)

    print("\n--- Final Response ---")
    print(final_state["messages"][-1].content)

    # Print Tool Calls if any
    for msg in final_state["messages"]:
        # Check for tool_calls attribute safely
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            print(f"\n[Tool Call] {tool_calls}")

    print("\n--- Loaded Tool Descriptions (Source for System Prompt) ---")
    for t in all_tools:
        if t.name in ["list_entities", "get_state", "turn_on"]:  # Show relevant ones
            print(f"- {t.name}: {t.description}")


if __name__ == "__main__":
    asyncio.run(main())
