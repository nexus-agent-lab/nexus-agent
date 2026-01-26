from langchain_core.tools import tool
from datetime import datetime
from functools import wraps
from typing import Callable, List

# Decorators for permissions (metadata)
def require_role(role: str):
    def decorator(func: Callable):
        func.required_role = role
        return func
    return decorator

@tool
@require_role("user")
def get_current_time() -> str:
    """Returns the current time in ISO format."""
    return datetime.now().isoformat()

@tool
@require_role("user") # Basic calculation is allowed for everyone
def calculate_number(a: int, b: int, operation: str) -> str:
    """Performs a calculation on two numbers. Operation can be 'add', 'subtract', 'multiply', 'divide'."""
    if operation == "add":
        return str(a + b)
    elif operation == "subtract":
        return str(a - b)
    elif operation == "multiply":
        return str(a * b)
    elif operation == "divide":
        if b == 0:
            return "Error: Division by zero"
        return str(a / b)
    else:
        return f"Error: Unknown operation {operation}"

@tool
@require_role("admin")
def dangerous_operation() -> str:
    """A tool only admins can use."""
    return "Performed dangerous operation!"

def get_tools() -> List[Callable]:
    """Returns a list of available tools."""
    # In a real dynamic system, we might scan modules or load from DB.
    # For Phase 2, we explicitly list them ensuring they have the metadata.
    return [get_current_time, calculate_number, dangerous_operation]
