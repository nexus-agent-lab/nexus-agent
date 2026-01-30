import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Type

# LangChain imports
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model

# MCP SDK imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client
    from mcp.types import CallToolResult
    from mcp.types import Tool as MCPToolModel
except ImportError:
    print("WARNING: 'mcp' module not found. MCP features will be disabled.")
    ClientSession = Any
    StdioServerParameters = Any
    sse_client = Any
    MCPToolModel = Any

logger = logging.getLogger("nexus.mcp")

CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", "/app/mcp_server_config.json")


class MCPManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
            cls._instance.exit_stack = AsyncExitStack()
            cls._instance.sessions: Dict[str, ClientSession] = {}  # server_name -> session
            cls._instance.tools: List[StructuredTool] = []
            cls._instance._config: Dict = {}
        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MCPManager()
        return cls._instance

    def _load_config(self):
        """Loads and parses the MCP configuration file."""
        if not os.path.exists(CONFIG_PATH):
            logger.warning(f"MCP config not found at {CONFIG_PATH}")
            self._config = {"mcpServers": {}}
            return

        try:
            with open(CONFIG_PATH, "r") as f:
                raw_config = json.load(f)
                self._config = self._expand_env_vars(raw_config)
            logger.info(f"Loaded MCP config with {len(self._config.get('mcpServers', {}))} servers.")
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            self._config = {"mcpServers": {}}

    def _expand_env_vars(self, obj):
        """Recursively expand environment variables in configuration values."""
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(v) for v in obj]
        elif isinstance(obj, str):
            return os.path.expandvars(obj)
        return obj

    async def initialize(self):
        """Connects to servers and caches tools."""
        self._load_config()
        servers = self._config.get("mcpServers", {})

        for name, server_conf in servers.items():
            if not server_conf.get("enabled", True):
                continue

            try:
                command = server_conf.get("command")
                args = server_conf.get("args", [])
                env = server_conf.get("env", None)
                required_role = server_conf.get("required_role", "user")

                # Check for SSE (URL) configuration first
                url = server_conf.get("url")

                read, write = None, None

                if url:
                    logger.info(f"Connecting to Remote MCP: {name} ({url}) [Role: {required_role}]...")
                    try:
                        # Headers to bypass local testing validation if needed
                        # Note: Server-side fix via MCP_TRANSPORT_SECURITY__ENABLE_DNS_REBINDING_PROTECTION is preferred
                        read, write = await self.exit_stack.enter_async_context(sse_client(url))
                    except Exception as e:
                        logger.error(f"Failed to connect to SSE MCP {name}: {e}")
                        continue

                elif command:
                    logger.info(f"Connecting to Local MCP: {name} ({command} {args}) [Role: {required_role}]...")
                    try:
                        server_params = StdioServerParameters(
                            command=command, args=args, env={**os.environ, **(env or {})}
                        )
                        read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
                    except Exception as e:
                        logger.error(f"Failed to connect to Stdio MCP {name}: {e}")
                        continue

                if not read or not write:
                    continue

                # Create session (Common for both Stdio and SSE)
                session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                self.sessions[name] = session

                # Fetch available tools
                mcp_tools_response = await session.list_tools()
                server_tool_config = server_conf.get("tool_config", {})

                for tool in mcp_tools_response.tools:
                    lc_tool = self._convert_to_langchain_tool(name, session, tool, required_role, server_tool_config)
                    self.tools.append(lc_tool)

                logger.info(f"Connected to {name}. Loaded {len(mcp_tools_response.tools)} tools.")

            except Exception as e:
                logger.error(f"Failed to connect to MCP server {name}: {e}")

    def _convert_to_langchain_tool(
        self,
        server_name: str,
        session: ClientSession,
        tool: MCPToolModel,
        required_role: str,
        tool_config_map: Dict = None,
    ) -> StructuredTool:
        tool_config_map = tool_config_map or {}

        async def _arun(**kwargs) -> str:
            try:
                from app.core.mcp_middleware import MCPMiddleware

                async def original_mcp_call(**k):
                    try:
                        result: CallToolResult = await session.call_tool(tool.name, arguments=k)
                        texts = [c.text for c in result.content if c.type == "text"]
                        raw_text = "\n".join(texts)
                        json_content = None
                        if raw_text.strip().startswith(("{", "[")):
                            try:
                                json_content = json.loads(raw_text)
                            except Exception:
                                pass
                        wrapper = (
                            {"type": "json", "content": json_content}
                            if json_content is not None
                            else {"type": "text", "content": raw_text}
                        )
                        return json.dumps(wrapper, ensure_ascii=False)
                    except Exception as e:
                        return json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)

                tool_conf = tool_config_map.get(tool.name, {})
                return await MCPMiddleware.call_tool(
                    tool_name=tool.name, args=kwargs, original_func=original_mcp_call, tool_config=tool_conf
                )
            except Exception as e:
                return f"MCP Tool Execution Error: {str(e)}"

        _arun.required_role = required_role
        from app.core.schema_utils import clean_schema

        cleaned_schema = clean_schema(tool.inputSchema)
        args_schema = self._create_args_schema(tool.name, cleaned_schema)

        return StructuredTool.from_function(
            coroutine=_arun,
            name=tool.name,
            description=f"[{server_name}] {tool.description or tool.name}",
            args_schema=args_schema,
        )

    def _create_args_schema(self, tool_name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
        fields = {}
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        for field_name, field_info in properties.items():
            field_type = str
            t = field_info.get("type", "string")
            if t == "integer":
                field_type = int
            elif t == "number":
                field_type = float
            elif t == "boolean":
                field_type = bool
            elif t == "array":
                field_type = List[Any]

            if field_name in required:
                fields[field_name] = (field_type, ...)
            else:
                fields[field_name] = (Optional[field_type], None)

        model_config = None
        if not properties:

            class Config:
                extra = "allow"

            model_config = Config
        model = create_model(f"{tool_name}Schema", **fields)
        if model_config:
            model.Config = model_config
        return model

    def get_tools(self) -> List[StructuredTool]:
        return self.tools

    @classmethod
    def get_system_instructions(cls) -> str:
        """Aggregates system instructions from all enabled servers."""
        inst = cls.get_instance()
        if not inst._config:
            inst._load_config()

        instructions = []
        servers_config = inst._config.get("mcpServers", {})
        for name, config in servers_config.items():
            if config.get("enabled", True):
                instruction = config.get("system_instruction")
                if instruction:
                    instructions.append(f"### {name.upper()} INSTRUCTIONS\n{instruction}")
        return "\n\n".join(instructions)

    async def cleanup(self):
        await self.exit_stack.aclose()


# Global accessor
_mcp_manager = MCPManager.get_instance()


async def get_mcp_tools() -> List[StructuredTool]:
    if not _mcp_manager.sessions:
        await _mcp_manager.initialize()
    return _mcp_manager.get_tools()


async def stop_mcp():
    await _mcp_manager.cleanup()
