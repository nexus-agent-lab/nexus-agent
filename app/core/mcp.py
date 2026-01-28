import json
import os
import asyncio
from typing import List, Dict, Any, Optional, Type
from contextlib import AsyncExitStack

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

# MCP SDK imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool as MCPToolModel, CallToolResult
except ImportError:
    # Fallback/Mock for environment where mcp is not installed yet (e.g. during dev before rebuild)
    # But in Docker it will be there.
    print("WARNING: 'mcp' module not found. MCP features will be disabled.")
    ClientSession = Any
    StdioServerParameters = Any
    MCPToolModel = Any

CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", "/app/mcp_server_config.json")

class MCPManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
            cls._instance.exit_stack = AsyncExitStack()
            cls._instance.sessions = {} # server_name -> session
            cls._instance.tools = []
        return cls._instance

    async def initialize(self):
        """
        Reads config, connects to servers, and caches tools.
        """
        if not os.path.exists(CONFIG_PATH):
            print(f"MCP Config not found at {CONFIG_PATH}. Skipping MCP init.")
            return

        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Failed to load MCP config: {e}")
            return

        servers = config.get("mcpServers", {})
        
        for name, server_conf in servers.items():
            command = server_conf.get("command")
            args = server_conf.get("args", [])
            env = server_conf.get("env", None)
            
            
            if not command:
                continue
                
            required_role = server_conf.get("required_role", "user")
            
            print(f"Connecting to MCP Server: {name} ({command} {args}) [Role: {required_role}]...")
            
            try:
                # Create connection parameters
                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env={**os.environ, **(env or {})}
                )
                
                # Establish connection
                # We use exit_stack to keep contexts alive indefinitely until app shutdown
                read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
                session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                
                await session.initialize()
                
                self.sessions[name] = session
                
                # Fetch available tools
                mcp_tools_response = await session.list_tools()
                
                # Get tool config for this server
                server_tool_config = server_conf.get("tool_config", {})
                
                # Convert to LangChain tools
                for tool in mcp_tools_response.tools:
                    lc_tool = self._convert_to_langchain_tool(name, session, tool, required_role, server_tool_config)
                    self.tools.append(lc_tool)
                    
                print(f"Connected to {name}. Loaded {len(mcp_tools_response.tools)} tools.")
                
            except Exception as e:
                print(f"Failed to connect to MCP server {name}: {e}")

    def _convert_to_langchain_tool(self, server_name: str, session: ClientSession, tool: MCPToolModel, required_role: str, tool_config_map: Dict = None) -> StructuredTool:
        """
        Wraps an MCP tool into a LangChain StructuredTool.
        """
        tool_config_map = tool_config_map or {}
        
        # Prepare tool config based on server name
        # We need access to the raw config dict to find tool_config
        # Ideally _convert_to_langchain_tool should receive server config
        # But for now let's modify the signature or access class state if possible.
        # Wait, initialize() has the config. Let's pass it down.
        
        async def _arun(**kwargs) -> str:
            """Async runner for the tool"""
            try:
                # Import here to avoid circular dependency
                from app.core.mcp_middleware import MCPMiddleware
                
                # We need to find the specific config for this tool
                # This requires passing 'tool_config' map to _convert_to_langchain_tool
                # But since we didn't update the signature yet, let's do a quick lookup if possible
                # or better, update the signature in the next step.
                # For now, let's assume we can get it.
                
                # Actually, let's just make the simple wrap first.
                # But wait, middleware requires 'original_func' to be a callable that takes kwargs.
                
                async def original_mcp_call(**k):
                    result: CallToolResult = await session.call_tool(tool.name, arguments=k)
                    texts = [c.text for c in result.content if c.type == 'text']
                    return "\n".join(texts)

                # Get config (we will update signature in next tool call)
                tool_conf = tool_config_map.get(tool.name, {}) if 'tool_config_map' in locals() else {}

                return await MCPMiddleware.call_tool(
                    tool_name=tool.name,
                    args=kwargs,
                    original_func=original_mcp_call,
                    tool_config=tool_conf
                )

            except Exception as e:
                return f"MCP Tool Execution Error: {str(e)}"
        
        # Attach permission attribute directly to the function wrapper so registry/agent can read it
        _arun.required_role = required_role

        from app.core.schema_utils import clean_schema

        # Dynamically create Pydantic model from JSON Schema
        # Clean schema to remove unsupported keywords and flatten anyOf/oneOf
        cleaned_schema = clean_schema(tool.inputSchema)
        args_schema = self._create_args_schema(tool.name, cleaned_schema)

        return StructuredTool.from_function(
            coroutine=_arun,
            name=tool.name, # E.g. "read_file"
            description=f"[{server_name}] {tool.description or tool.name}",
            args_schema=args_schema
        )

    def _create_args_schema(self, tool_name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
        """
        Converts MCP JSON Schema to Pydantic Model.
        """
        fields = {}
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        
        for field_name, field_info in properties.items():
            field_type = str
            # Basic type mapping
            t = field_info.get("type", "string")
            if t == "integer":
                field_type = int
            elif t == "number":
                field_type = float
            elif t == "boolean":
                field_type = bool
            elif t == "array":
                field_type = List[Any]
            
            # description
            description = field_info.get("description", "")
            
            if field_name in required:
                fields[field_name] = (field_type, ...) # Required
            else:
                fields[field_name] = (Optional[field_type], None) # Optional

        # If schema is empty (no properties), allow extra arguments (e.g. for HA tools with missing schemas)
        # Otherwise, stick to defaults (usually extra='ignore' or 'forbid')
        model_config = None
        if not properties:
             # Create a config class to allow extra fields
             class Config:
                 extra = "allow"
             model_config = Config

        model = create_model(f"{tool_name}Schema", **fields)
        if model_config:
            model.Config = model_config
            
        return model

    def get_tools(self) -> List[StructuredTool]:
        return self.tools

    async def cleanup(self):
        await self.exit_stack.aclose()

# Global accessor
_mcp_manager = MCPManager()

async def get_mcp_tools() -> List[StructuredTool]:
    if not _mcp_manager.sessions:
        await _mcp_manager.initialize()
    return _mcp_manager.get_tools()
