"""
Dump the exact LLM request body for a temperature query.
Run inside the container: docker-compose exec -T nexus-app python scripts/dump_wire_log.py
"""
import asyncio
import json
import os
import sys

sys.path.append(os.getcwd())


async def main():
    from app.core.agent import get_llm
    from app.core.mcp_manager import get_mcp_tools
    from app.core.tool_router import tool_router
    from app.tools.registry import get_static_tools

    # 1. Register tools (same as main.py startup)
    static_tools = get_static_tools()
    mcp_tools = await get_mcp_tools()
    all_tools = static_tools + mcp_tools
    await tool_router.register_tools(all_tools)

    # 2. Simulate routing for "查一下家里的温度"
    query = "查一下家里的温度"
    selected = await tool_router.route(query)

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Total tools: {len(all_tools)}, Routed tools: {len(selected)}")
    print(f"{'='*60}")
    print("\n📋 ROUTED TOOL LIST:")
    for t in selected:
        desc = getattr(t, "description", "")[:100]
        print(f"  ✅ {t.name}: {desc}")

    # 3. Show the actual JSON Schema sent via bind_tools
    llm = get_llm()
    llm_with_tools = llm.bind_tools(selected)

    # Extract tool schemas from the bound model
    tool_schemas = llm_with_tools.kwargs.get("tools", [])

    print(f"\n{'='*60}")
    print("📤 ACTUAL `tools` PARAMETER IN LLM API REQUEST:")
    print(f"{'='*60}")
    print(json.dumps(tool_schemas, ensure_ascii=False, indent=2))

    # 4. Show the full request body (messages + tools)
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content="You are Nexus, an AI assistant. (truncated for brevity)"),
        HumanMessage(content=query),
    ]

    # Convert to OpenAI format
    from langchain_core.messages import message_to_dict

    msgs_dicts = [message_to_dict(m) for m in messages]

    full_body = {
        "model": os.getenv("LLM_MODEL", "unknown"),
        "messages": msgs_dicts,
        "tools": tool_schemas,
        "temperature": 0,
    }

    print(f"\n{'='*60}")
    print("📦 COMPLETE LLM API REQUEST BODY (simplified):")
    print(f"{'='*60}")
    print(json.dumps(full_body, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
