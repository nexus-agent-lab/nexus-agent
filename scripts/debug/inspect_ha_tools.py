
import asyncio
import os
from mcp import ClientSession
from mcp.client.sse import sse_client

async def inspect():
    url = "http://localhost:8080/sse"
    print(f"Connecting to {url}...")
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_res = await session.list_tools()
                
                for tool in tools_res.tools:
                    print(f"\n[{tool.name}]")
                    print(f"  Description: {tool.description}")
                    print(f"  Schema: {tool.inputSchema}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
