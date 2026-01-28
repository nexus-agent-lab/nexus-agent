import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def inspect_raw():
    server_path = "/app/external_mcp/mcp-homeassistant/build/index.js"
    if not os.path.exists(server_path):
        print(f"Server not found at {server_path}")
        return

    print(f"Connecting to {server_path}...")
    server_params = StdioServerParameters(
        command="node", # executing js file needs node
        args=[server_path],
        env=dict(os.environ) # copy env
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.list_tools()
            for tool in result.tools:
                if tool.name in ["get_state", "call_service", "list_entities"]:
                    print(f"--- Tool: {tool.name} ---")
                    print(json.dumps(tool.inputSchema, indent=2))
            
if __name__ == "__main__":
    asyncio.run(inspect_raw())
