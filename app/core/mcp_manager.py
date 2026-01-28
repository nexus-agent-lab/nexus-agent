import json
import subprocess
import os
import signal
import logging
from typing import Dict, Optional, List

logger = logging.getLogger("nexus.mcp")

CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", "mcp_server_config.json")

class MCPManager:
    _instance = None
    _servers: Dict[str, subprocess.Popen] = {}
    _config: Dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def load_config(cls):
        """Loads and parses the MCP configuration file."""
        if not os.path.exists(CONFIG_PATH):
            logger.warning(f"MCP config not found at {CONFIG_PATH}")
            cls._config = {"mcpServers": {}}
            return

        try:
            with open(CONFIG_PATH, 'r') as f:
                cls._config = json.load(f)
            logger.info(f"Loaded MCP config with {len(cls._config.get('mcpServers', {}))} servers.")
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            cls._config = {"mcpServers": {}}

    @classmethod
    def start_all(cls):
        """Starts all enabled MCP servers defined in config."""
        cls.load_config()
        servers = cls._config.get("mcpServers", {})
        
        for name, config in servers.items():
            if config.get("enabled", True):
                cls.start_server(name, config)

    @classmethod
    def start_server(cls, name: str, config: Dict):
        """Starts a single MCP server subprocess."""
        if name in cls._servers:
            logger.info(f"MCP Server '{name}' is already running.")
            return

        command = config.get("command")
        args = config.get("args", [])
        cwd = config.get("cwd", os.getcwd())
        env = config.get("env", os.environ.copy())

        if not command:
            logger.error(f"No command specified for MCP server '{name}'")
            return

        # Prepare Environment Variables
        # 1. Start with system environment (or a cleaner subset if strict isolation is desired)
        # For compatibility, we copy system env, but we could filter sensitive global keys if needed.
        proc_env = os.environ.copy()

        # 2. Local .env file loading (Per-MCP Isolation)
        # If 'cwd' is set, look for .env there
        if cwd and os.path.exists(os.path.join(cwd, ".env")):
            try:
                from dotenv import dotenv_values
                local_env = dotenv_values(os.path.join(cwd, ".env"))
                logger.info(f"Loaded {len(local_env)} variables from local .env for '{name}'")
                proc_env.update(local_env)
            except ImportError:
                logger.warning("python-dotenv not installed. Skipping local .env loading.")
            except Exception as e:
                logger.error(f"Error loading local .env: {e}")
        
        # 3. Merge config 'env' with variable expansion support
        # This overrides local .env if collision occurs (Configuration takes precedence)
        config_env = config.get("env", {})
        for key, value in config_env.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Expand ${VAR_NAME}
                var_name = value[2:-1]
                # Look in proc_env first (so we can reference local .env vars), then system
                env_val = proc_env.get(var_name) or os.getenv(var_name)
                if env_val:
                    proc_env[key] = env_val
                else:
                    logger.warning(f"Environment variable {var_name} not found for server '{name}'")
            else:
                proc_env[key] = str(value)

        try:
            logger.info(f"Starting MCP Server '{name}': {command} {args} (CWD: {cwd})")
            
            process = subprocess.Popen(
                [command] + args,
                cwd=cwd,
                env=proc_env,
            )
            cls._servers[name] = process
            logger.info(f"MCP Server '{name}' started (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Failed to start MCP Server '{name}': {e}")

    @classmethod
    def stop_server(cls, name: str):
        """Stops a running MCP server."""
        process = cls._servers.get(name)
        if process:
            logger.info(f"Stopping MCP Server '{name}'...")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping server '{name}': {e}")
            
            del cls._servers[name]
        else:
            logger.warning(f"MCP Server '{name}' is not running.")

    @classmethod
    def stop_all(cls):
        """Stops all running MCP servers."""
        # Convert keys to list to avoid runtime error during iteration
        for name in list(cls._servers.keys()):
            cls.stop_server(name)

    @classmethod
    def reload(cls):
        """Restarts all servers with fresh config."""
        logger.info("Reloading MCP Manager...")
        cls.stop_all()
        cls.start_all()
        logger.info("MCP Manager reload complete.")

    @classmethod
    def get_status(cls) -> List[Dict]:
        """Returns the status of all configured servers."""
        status_list = []
        servers_config = cls._config.get("mcpServers", {})
        
        for name, config in servers_config.items():
            process = cls._servers.get(name)
            is_running = process is not None and process.poll() is None
            
            status_list.append({
                "name": name,
                "enabled": config.get("enabled", True),
                "status": "Running" if is_running else "Stopped",
                "pid": process.pid if is_running else None,
                "source": config.get("source", "unknown"),
                "description": config.get("description", "")
            })
        return status_list

    @classmethod
    def get_system_instructions(cls) -> str:
        """Aggregates system instructions from all enabled servers."""
        instructions = []
        servers_config = cls._config.get("mcpServers", {})
        
        for name, config in servers_config.items():
            if config.get("enabled", True):
                instruction = config.get("system_instruction")
                if instruction:
                    instructions.append(f"### {name.upper()} INSTRUCTIONS\n{instruction}")
        
        return "\n\n".join(instructions)
