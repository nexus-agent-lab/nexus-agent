from datetime import datetime
from typing import Callable, List

from langchain_core.tools import tool

from app.core.decorators import require_role
from app.tools.memory_tools import save_insight, store_preference
from app.tools.sandbox import get_sandbox_tool
from app.tools.learning_tools import learn_skill_rule


@tool
@require_role("user")
def get_current_time() -> str:
    """Returns the current time in ISO format."""
    return datetime.now().isoformat()


@tool
@require_role("user")  # Basic calculation is allowed for everyone
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


def get_static_tools() -> List[Callable]:
    """Returns the list of static tools."""
    return [get_current_time, calculate_number, dangerous_operation, get_sandbox_tool(), store_preference, save_insight, learn_skill_rule]
