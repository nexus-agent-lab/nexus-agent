from mcp.server.fastmcp import FastMCP

# Define a simple MCP server using FastMCP
mcp = FastMCP("demo_server")


@mcp.tool()
def internal_api_tool(query: str) -> str:
    """Administrative tool to query status. Authorized use only."""
    return f"Internal Database Result for '{query}': [SECRET_DATA_123]"


if __name__ == "__main__":
    mcp.run()
