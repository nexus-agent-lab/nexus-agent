from typing import List

# Policy Definition
# Role-based and Context-based access control

# Tool Tags Definition
# Tools should be registered with these tags
# e.g., @tool(tags=["home", "read_only"])


class PolicyMatrix:
    # Role Permissions (What can this role do?)
    ROLE_POLICIES = {
        "admin": ["*"],  # Superuser access
        "user": ["tag:safe", "tag:home"],  # Standard user
        "guest": ["tag:read_only"],
    }

    # Context Permissions (What is allowed in this environment?)
    # If explicit context is provided, it acts as a filter on top of Role
    CONTEXT_POLICIES = {
        "home": ["tag:home", "tag:safe", "tag:personal"],
        "work": ["tag:work", "tag:enterprise", "tag:safe"],
        "public": ["tag:read_only"],
    }

    @staticmethod
    def is_allowed(user_role: str, context: str, tool_tags: List[str]) -> bool:
        """
        Determines if access is granted based on Intersection of Role and Context.
        Access is granted if AT LEAST ONE of the tool's tags is allowed by BOTH
        the Role Policy AND the Context Policy.
        """
        allowed_by_role = PolicyMatrix.ROLE_POLICIES.get(user_role, [])
        allowed_by_context = PolicyMatrix.CONTEXT_POLICIES.get(context, [])

        # 1. Admin Override
        if "*" in allowed_by_role:
            return True

        # 2. Check Role (Must match at least one tag)
        role_match = False
        for tag in tool_tags:
            if tag in allowed_by_role:
                role_match = True
                break

        if not role_match:
            return False

        # 3. Check Context (If context is specified, must match at least one tag)
        if context:
            context_match = False
            # Allow "*" in context policy too if needed, but usually contexts are restrictive
            if "*" in allowed_by_context:
                return True

            for tag in tool_tags:
                if tag in allowed_by_context:
                    context_match = True
                    break
            if not context_match:
                return False

        return True
