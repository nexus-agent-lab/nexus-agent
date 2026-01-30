from functools import wraps
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


def with_user(optional: bool = True):
    """
    Decorator to fetch the User object based on 'user_id' in kwargs.
    It injects the 'user' object into kwargs for the decorated function.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id")
            user = None
            if user_id:
                from app.core.db import AsyncSessionLocal
                from app.models.user import User

                async with AsyncSessionLocal() as session:
                    user = await session.get(User, user_id)

            if not optional and not user:
                return "❌ Error: user_id is required or invalid."

            # Inject user object
            kwargs["user_object"] = user
            return await func(*args, **kwargs)

        return wrapper

    return decorator
