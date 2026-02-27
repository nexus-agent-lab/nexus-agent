import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Type
from urllib.parse import urlparse

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


# Whitelist of allowed MCP server commands for security
ALLOWED_MCP_COMMANDS = ["python", "python3", "node", "npx", "uv"]

# Allowlist of allowed hostnames for SSE MCP servers (SSRF protection)
ALLOWED_SSE_HOSTNAMES = ["localhost", "127.0.0.1", "host.docker.internal", "mcp-homeassistant", "lark-mcp"]


class MCPManager:
    _instance = None
    _lock = asyncio.Lock()  # Protect initialization
    _db_plugins: Dict[str, Any] = {}

    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, ClientSession] = {}  # server_name -> session
        self.tools: List[StructuredTool] = []
        self._initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MCPManager()
        return cls._instance

    async def _load_from_db(self) -> Optional[Dict[str, Any]]:
        """Fetches enabled plugins from the database."""
        try:
            from sqlalchemy import select

            from app.core.db import AsyncSessionLocal
            from app.models.plugin import Plugin

            # Load catalog manifest
            catalog_dict = {}
            try:
                with open(os.path.join(os.getcwd(), "plugin_catalog.json"), "r") as f:
                    catalog = json.load(f)
                    for item in catalog:
                        catalog_dict[item["id"]] = item
            except FileNotFoundError:
                logger.warning("plugin_catalog.json not found")
            except Exception as e:
                logger.error(f"Failed to load plugin catalog: {e}")

            async with AsyncSessionLocal() as session:
                statement = select(Plugin).where(Plugin.status == "active")
                result = await session.execute(statement)
                plugins = result.scalars().all()

                if not plugins:
                    return {}

                servers = {}
                for p in plugins:
                    # Merge basic fields with config JSON
                    conf = p.config.copy() if p.config else {}

                    if p.manifest_id and p.manifest_id in catalog_dict:
                        catalog_entry = catalog_dict[p.manifest_id]

                        # Merge config defaults
                        cat_config = catalog_entry.get("config", {})
                        for k, v in cat_config.items():
                            if k not in conf:
                                conf[k] = v

                        # Override url/source_url if not defined in DB
                        if not p.source_url and "source_url" in catalog_entry:
                            p.source_url = catalog_entry["source_url"]

                        # Inject allowed hostnames
                        for host in catalog_entry.get("allowed_hostnames", []):
                            if host not in ALLOWED_SSE_HOSTNAMES:
                                ALLOWED_SSE_HOSTNAMES.append(host)

                        # Use catalog required_role if present
                        if "required_role" in catalog_entry:
                            conf["required_role"] = catalog_entry["required_role"]

                    if p.source_url and not conf.get("url"):
                        conf["url"] = p.source_url

                    # Ensure required_role from plugin DB is set
                    if "required_role" not in conf and p.required_role:
                        conf["required_role"] = p.required_role

                    # Store plugin ID for secret fetching
                    conf["plugin_id"] = p.id

                    # Ensure name is consistent
                    servers[p.name] = conf

                # Deduplicate by source_url to prevent double-loading
                seen_urls = {}
                for name, conf in list(servers.items()):
                    url = conf.get("url")
                    if url and url in seen_urls:
                        logger.warning(
                            f"Duplicate source_url detected: '{name}' conflicts with '{seen_urls[url]}'. Skipping '{name}'."
                        )
                        del servers[name]
                    elif url:
                        seen_urls[url] = name

                MCPManager._db_plugins = servers
                return servers

        except Exception as e:
            logger.error(f"Failed to load MCP config from DB: {e}")
            return None

    async def _fetch_global_secrets(self, plugin_id: int) -> Dict[str, str]:
        """Fetches and decrypts global secrets for a plugin."""
        try:
            from sqlalchemy import select

            from app.core.db import AsyncSessionLocal
            from app.core.security import decrypt_secret
            from app.models.secret import Secret, SecretScope

            async with AsyncSessionLocal() as session:
                statement = select(Secret).where(
                    Secret.plugin_id == plugin_id, Secret.scope == SecretScope.global_scope
                )
                result = await session.execute(statement)
                secrets = result.scalars().all()

                return {s.key: decrypt_secret(s.encrypted_value) for s in secrets}
        except Exception as e:
            logger.error(f"Failed to fetch global secrets for plugin {plugin_id}: {e}")
            return {}

    async def initialize(self):
        """Connects to servers and caches tools."""
        async with self._lock:
            if self._initialized:
                return

            # DB is now the single source of truth for installed plugins
            db_servers = await self._load_from_db()
            servers = db_servers if db_servers else {}

            for name, server_conf in servers.items():
                if not server_conf.get("enabled", True):
                    continue
                # Fetch global secrets if plugin_id is present
                global_secrets = {}
                plugin_id = server_conf.get("plugin_id")
                if plugin_id:
                    global_secrets = await self._fetch_global_secrets(plugin_id)

                try:
                    command = server_conf.get("command")
                    args = server_conf.get("args", [])
                    env = server_conf.get("env", None)
                    required_role = server_conf.get("required_role", "user")

                    # Check for SSE (URL) configuration first
                    url = server_conf.get("url")

                    read, write = None, None

                    if url:
                        # SSRF protection: validate hostname against allowlist
                        parsed_url = urlparse(url)
                        hostname = parsed_url.hostname
                        if hostname not in ALLOWED_SSE_HOSTNAMES:
                            logger.warning(
                                f"SSRF protection: Skipping MCP server '{name}' with disallowed hostname '{hostname}'. "
                                f"Allowed hostnames: {ALLOWED_SSE_HOSTNAMES}"
                            )
                            continue

                        logger.info(f"Connecting to Remote MCP: {name} ({url}) [Role: {required_role}]...")
                        try:
                            # Headers to bypass local testing validation if needed
                            # Note: Server-side fix via MCP_TRANSPORT_SECURITY__ENABLE_DNS_REBINDING_PROTECTION is preferred
                            read, write = await self.exit_stack.enter_async_context(
                                sse_client(url, headers=global_secrets)
                            )
                        except Exception as e:
                            logger.error(f"Failed to connect to SSE MCP {name}: {e}")
                            continue

                    elif command:
                        # Security check: validate command against whitelist
                        if command not in ALLOWED_MCP_COMMANDS:
                            logger.critical(
                                f"SECURITY ALERT: MCP server '{name}' uses forbidden command '{command}'. Allowed commands: {ALLOWED_MCP_COMMANDS}. Skipping server."
                            )
                            continue

                        logger.info(f"Connecting to Local MCP: {name} ({command} {args}) [Role: {required_role}]...")
                        try:
                            server_params = StdioServerParameters(
                                command=command, args=args, env={**os.environ, **(env or {}), **global_secrets}
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
                        lc_tool = self._convert_to_langchain_tool(
                            name, session, tool, required_role, server_tool_config, plugin_id
                        )
                        self.tools.append(lc_tool)

                    logger.info(f"Connected to {name}. Loaded {len(mcp_tools_response.tools)} tools.")

                except Exception as e:
                    logger.error(f"Failed to connect to MCP server {name}: {e}")

            self._initialized = True

    def _convert_to_langchain_tool(
        self,
        server_name: str,
        session: ClientSession,
        tool: MCPToolModel,
        required_role: str,
        tool_config_map: Dict = None,
        plugin_id: Optional[int] = None,
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

                tool_conf = tool_config_map.get(tool.name, {}).copy()
                if plugin_id:
                    tool_conf["plugin_id"] = plugin_id
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
            metadata={"category": server_name},
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
        instructions = []
        for name, config in cls._db_plugins.items():
            if config.get("enabled", True):
                instruction = config.get("system_instruction")
                if instruction:
                    instructions.append(f"### {name.upper()} INSTRUCTIONS\n{instruction}")
        return "\n\n".join(instructions)

    async def reload(self):
        """Hot-swaps MCP servers by cleaning up and re-initializing."""
        logger.info("Reloading MCP servers from DB/Config...")

        # Handle connection errors gracefully by checking DB before cleanup
        db_servers = await self._load_from_db()
        if db_servers is None:
            logger.error("Failed to connect to DB during reload. Keeping existing sessions.")
            return

        await self.cleanup()
        await self.initialize()

    async def cleanup(self):
        async with self._lock:
            await self.exit_stack.aclose()
            self.sessions.clear()
            self.tools.clear()
            self._initialized = False


# Global accessor
_mcp_manager = MCPManager.get_instance()


async def get_mcp_tools() -> List[StructuredTool]:
    if not _mcp_manager._initialized:
        await _mcp_manager.initialize()
    return _mcp_manager.get_tools()


async def stop_mcp():
    await _mcp_manager.cleanup()
