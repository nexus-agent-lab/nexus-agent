import requests
import sys

def test_chat(query):
    url = "http://localhost:8000/chat"
    headers = {"X-API-Key": "nexus_admin_key"} # Assuming dev setup uses this or skip if auth disabled locally
    # Actually, auth is get_current_user depending on get_session
    # For local testing within docker container, we might need a valid API key or mock.
    # But wait, we are running this script FROM Host or Container?
    # If from Host, we need the port.
    # Let's assume we run this inside the container for simplicity of network.
    
    # In docker-compose, nexus-app exposes 8000.
    
    # Auth bypass: The User model needs an API Key. 
    # Since we are solving "LLM Logic", using a script inside the container with direct python call to graph is better 
    # than HTTP to avoid Auth complexity for now.
    pass

# Redoing as direct python invocation script
import asyncio
import os
import sys

# Add app to path
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage
from app.core.agent import create_agent_graph
from app.core.mcp import get_mcp_tools
from app.tools.registry import get_static_tools
from app.models.user import User
import logging

# Enable HTTP logging to see Payload & URL
logging.basicConfig(level=logging.WARN)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.DEBUG)

async def main():
    print(f"--- Testing Query: '{sys.argv[1]}' ---")
    
    # Check Env
    import os
    print(f"[Debug] LLM_BASE_URL: {os.getenv('LLM_BASE_URL', 'Not Set')}")
    print(f"[Debug] LLM_MODEL: {os.getenv('LLM_MODEL', 'Not Set')}")
    
    # Setup Tools
    static_tools = get_static_tools()
    try:
        mcp_tools = await get_mcp_tools()
    except:
        mcp_tools = []
    
    all_tools = static_tools + mcp_tools
    print(f"Loaded {len(all_tools)} tools.")
    
    # Create Graph
    graph = create_agent_graph(all_tools)
    
    # Mock User
    mock_user = User(id=1, username="tester", role="admin")
    
    # Invoke
    initial_state = {
        "messages": [HumanMessage(content=sys.argv[1])],
        "user": mock_user
    }
    
    print("Invoking Agent...")
    final_state = await graph.ainvoke(initial_state)
    
    print("\n--- Final Response ---")
    print(final_state["messages"][-1].content)
    
    # Print Tool Calls if any
    for msg in final_state["messages"]:
        # Check for tool_calls attribute safely
        tool_calls = getattr(msg, 'tool_calls', None)
        if tool_calls:
            print(f"\n[Tool Call] {tool_calls}")

    print("\n--- Loaded Tool Descriptions (Source for System Prompt) ---")
    for t in all_tools:
        if t.name in ["list_entities", "get_state", "turn_on"]: # Show relevant ones
            print(f"- {t.name}: {t.description}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_chat.py 'Your question'")
        sys.exit(1)
    asyncio.run(main())
