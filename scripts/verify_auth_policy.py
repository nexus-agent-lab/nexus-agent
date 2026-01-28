import asyncio
import uuid

# Mock DB for independent testing
from unittest.mock import patch

from app.core.audit import AuditInterceptor
from app.core.policy import PolicyMatrix


async def mock_create_audit(trace_id, user_id, action, tool_name, tool_args):
    print(f"   [MockDB] Logged Action: {action} | Status: PENDING")
    return 1


async def mock_update_audit(log_id, status, duration, error):
    print(f"   [MockDB] Updated Log #{log_id}: Status={status}, Error={error}")


def test_policy_logic():
    print("\n--- 1. Testing Policy Matrix Logic ---")

    # Grid of scenarios
    # User | Context | Tool Tags | Expected
    scenarios = [
        ("admin", "work", ["tag:enterprise"], True, "Admin should access everything"),
        ("user", "home", ["tag:enterprise"], False, "User should NOT access enterprise tool"),
        ("user", "work", ["tag:enterprise"], False, "User Role restriction applies even in Work context"),
        ("user", "home", ["tag:safe"], True, "User can access safe tool in Home"),
        ("user", "work", ["tag:safe"], True, "User can access safe tool in Work"),
        ("guest", "public", ["tag:read_only"], True, "Guest can access read_only"),
        ("guest", "public", ["tag:safe"], False, "Guest cannot access tag:safe (only read_only)"),
    ]

    passed = 0
    for role, ctx, tags, expected, desc in scenarios:
        result = PolicyMatrix.is_allowed(role, ctx, tags)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        print(f"{status} {desc}: Role={role}, Ctx={ctx}, Tags={tags} -> {result}")

    print(f"Policy Tests: {passed}/{len(scenarios)} Passed")


@patch("app.core.audit.create_audit_entry", side_effect=mock_create_audit)
@patch("app.core.audit.update_audit_entry", side_effect=mock_update_audit)
async def test_interceptor(mock_create, mock_update):
    print("\n--- 2. Testing Audit Interceptor Enforcement ---")

    trace_id = uuid.uuid4()

    # Case A: Allowed Access
    print("\n(A) Simulating Allowed Access (User/Home -> tag:safe)")
    try:
        async with AuditInterceptor(
            trace_id=trace_id,
            user_id=1,
            tool_name="calculator",
            tool_args={"a": 1},
            user_role="user",
            context="home",
            tool_tags=["tag:safe"],
        ):
            print("   Executing Tool...")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
    else:
        print("✅ Access Granted as expected.")

    # Case B: Denied Access
    print("\n(B) Simulating Denied Access (User/Home -> tag:enterprise)")
    try:
        async with AuditInterceptor(
            trace_id=trace_id,
            user_id=1,
            tool_name="delete_database",
            tool_args={},
            user_role="user",
            context="home",
            tool_tags=["tag:enterprise"],
        ):
            print("❌ Start Tool Execution (Should NOT happen)")
    except PermissionError as e:
        print(f"✅ Caught Expected Permission Error: {e}")
    except Exception as e:
        print(f"❌ Wrong Error type caught: {e}")


if __name__ == "__main__":
    test_policy_logic()
    asyncio.run(test_interceptor())
