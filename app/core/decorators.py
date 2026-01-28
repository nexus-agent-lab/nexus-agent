from typing import Callable


# Decorators for permissions (metadata)
def require_role(role: str):
    def decorator(func: Callable):
        # Handle both functions and classes (though classes usually use a different mechanism)
        # For LangChain tools, we often set attributes on the function or the instance.
        # If applied to a function tool:
        func.required_role = role
        return func

    return decorator
