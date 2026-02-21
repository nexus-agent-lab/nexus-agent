import os
import subprocess
import sys
import tempfile
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.decorators import require_role


class SandboxInput(BaseModel):
    code: str = Field(description="The Python code to execute safely.")


SANDBOX_PRELUDE = """
import sys
import os

def _sandbox_audit_hook(event, args):
    # 1. Prevent process execution
    if event in ('os.system', 'subprocess.Popen', 'os.exec', 'os.spawn', 'os.fork', 'os.posix_spawn', 'os.kill'):
        raise RuntimeError(f"Forbidden process execution: {event}")

    # 2. Prevent network access
    if event in ('socket.connect', 'socket.bind', 'socket.sendto', 'socket.getaddrinfo'):
        raise RuntimeError(f"Forbidden network access: {event}")

    # 3. Block unauthorized filesystem modifications
    if event in ('os.chmod', 'os.chown', 'os.remove', 'os.unlink', 'os.rmdir', 'os.rename', 'os.mkdir', 'os.link', 'os.symlink', 'os.replace'):
        raise RuntimeError(f"Forbidden filesystem modification: {event}")

    # 4. Restrict file access to allowed zones and internal imports
    if event in ('open', 'io.open_code'):
        path = args[0]
        if path is None: return
        try:
            abs_path = os.path.abspath(str(path))
        except Exception:
            abs_path = str(path)

        # Allow read/write access to sandbox_data and tmp
        # also handle macos temp dirs starting with /var/folders
        if abs_path.startswith('/app/storage/sandbox_data') or abs_path.startswith('/tmp') or abs_path.startswith(os.environ.get("TMPDIR", "/tmp")) or abs_path.startswith('/var/folders'):
            return

        # Allow read-only access to system libraries for imports
        # Flags bitmask check (O_WRONLY=1, O_RDWR=2, O_CREAT=64, O_TRUNC=512, O_APPEND=1024)
        write_flags = 1 | 2 | 64 | 512 | 1024
        flags = args[2] if (event == 'open' and len(args) > 2) else 0

        if not (flags & write_flags):
            # Define allowed system/library prefixes
            system_prefixes = {sys.prefix, sys.base_prefix, '/usr/', '/lib/', '/etc/python', '/proc/', '/dev/urandom', '/System/Library/', '/Library/', os.path.expanduser('~/.pyenv'), os.path.expanduser('~/Library/Caches')}
            # Include all absolute paths from sys.path to support site-packages/venv imports
            for p in sys.path:
                if p and os.path.isabs(p):
                    system_prefixes.add(p)

            if any(abs_path.startswith(p) for p in system_prefixes if p):
                return

        raise RuntimeError(f"Forbidden file access: {abs_path}")

sys.addaudithook(_sandbox_audit_hook)

# --- USER CODE BEGINS HERE ---
"""


class PythonSandboxTool(BaseTool):
    name: str = "python_sandbox"
    description: str = (
        "Executes Python code in a sandboxed environment. "
        "Use this for complex calculations, data processing, or running scripts. "
        "Input should be valid Python code as a string."
    )
    args_schema: Type[BaseModel] = SandboxInput

    # Custom attribute for RBAC - user level is sufficient for data processing
    required_role: str = "user"

    def _run(self, code: str) -> str:
        """Execute the code using subprocess (same container, limited duration)."""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(SANDBOX_PRELUDE + code)
                script_path = f.name

            try:
                # Use a local path for local testing if /app doesn't exist
                cwd = (
                    "/app/storage/sandbox_data"
                    if os.path.exists("/app/storage/sandbox_data")
                    else tempfile.gettempdir()
                )

                # Execute with timeout and capture output
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd=cwd,
                )

                if result.returncode != 0:
                    return f"Execution Error:\n{result.stderr}"

                return result.stdout or "(No output)"

            finally:
                # Clean up temp file
                if os.path.exists(script_path):
                    os.remove(script_path)

        except subprocess.TimeoutExpired:
            return "Error: Execution timed out (30s limit)"
        except Exception as e:
            return f"Sandbox Error: {str(e)}"

    async def _arun(self, code: str):
        """Async version - runs sync _run in executor."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, code)


# Register logic will be in registry.py, but we define the class and decorator attribute here.
@require_role("admin")
def get_sandbox_tool():
    return PythonSandboxTool()
