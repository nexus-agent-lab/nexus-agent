from typing import Optional, Type, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
import subprocess
import tempfile
import os

from app.core.decorators import require_role

class SandboxInput(BaseModel):
    code: str = Field(description="The Python code to execute safely.")

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
            # Write code to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                script_path = f.name
            
            try:
                # Execute with timeout and capture output
                result = subprocess.run(
                    ['python', script_path],
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd='/app/storage/sandbox_data'  # Set working dir to data folder
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
