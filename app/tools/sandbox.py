from typing import Optional, Type, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
import docker
import textwrap

from app.core.decorators import require_role

class SandboxInput(BaseModel):
    code: str = Field(description="The Python code to execute safely.")

class PythonSandboxTool(BaseTool):
    name: str = "python_sandbox"
    description: str = (
        "Executes Python code in a secure, isolated Docker container. "
        "Use this for complex calculations, data processing, or running scripts. "
        "Input should be valid Python code as a string."
    )
    args_schema: Type[BaseModel] = SandboxInput
    
    # Custom attribute for RBAC
    required_role: str = "admin"

    def _run(self, code: str) -> str:
        """Execute the code in a Docker container."""
        client = docker.from_env()
        container = None
        try:
            # Prepare code wrapper to handle printing output safely if needed
            # But specific instructions said "write code to script.py and run it"
            
            # Start ephemeral container
            container = client.containers.run(
                image="python:3.10-slim",
                # command="python script.py", # Removed to avoid duplicate
                detach=True,
                network_mode="none",  # No internet access
                mem_limit="128m",     # Limit memory
                # We need to inject the code. 
                # Since 'mounts' might be tricky if we don't want to rely on host FS,
                # we can use 'run' with a sleep command, inject code, then exec.
                # OR we can pass the code as a string to python -c.
                # The user requested: "write code to script.py" inside container.
                # The cleanest way without mounting host files is:
                # 1. Start container with command to sleep
                # 2. Exec command to write file
                # 3. Exec verify/run
                # However, client.containers.run is blocking if not detached.
                # Let's try: run with a command that writes the file and runs it.
                # command=f"sh -c 'echo \"{escaped_code}\" > script.py && python script.py'"
                # This is prone to escaping issues.
                # Easier: Start container, use put_archive (tar) or just simple exec loop?
                
                # Simple approach requested:
                # "Start a temporary container... write code to script.py... execute python script.py"
                # To do this reliably with docker-py:
                tty=True,
                command="/bin/bash" # Start keeping it alive
            )
            
            # Simple file injection via exec echo (careful with quotes)
            # Or use socket. 
            # Let's use a robust way: executing a python one-liner to write the file, or just use python -c directly?
            # User specifically asked for "write code to script.py".
            
            # Let's write the file using python inside the container to avoid shell escaping hell
            # We can pass the code via stdin if we use socket, but docker-py exec_run doesn't easily streaming stdin.
            
            # Let's try writing via a simple echo, but hex-encoded to avoid special chars?
            # Or just use the fact that input is a string.
            
            # Use base64 for robust code injection
            import base64
            b64_code = base64.b64encode(code.encode("utf-8")).decode("utf-8")
            
            # Write code using python one-liner inside container
            write_cmd = f"python -c \"import base64; open('script.py', 'wb').write(base64.b64decode('{b64_code}'))\""
            
            exit_code, output = container.exec_run(write_cmd)
            if exit_code != 0:
                return f"System Error: Failed to write code to container. {output.decode('utf-8')}"
                
            # Now run it
            exit_code, output = container.exec_run("python script.py")
            stdout = output.decode("utf-8")
            
            if exit_code != 0:
                return f"Execution Error:\n{stdout}"
            
            return stdout

        except Exception as e:
            return f"Sandbox Error: {str(e)}"
        finally:
            if container:
                try:
                    container.stop(timeout=1)
                    container.remove()
                except:
                    pass

    def _arun(self, code: str):
        raise NotImplementedError("Async not implemented yet")

# Register logic will be in registry.py, but we define the class and decorator attribute here.
@require_role("admin")
def get_sandbox_tool():
    return PythonSandboxTool()
