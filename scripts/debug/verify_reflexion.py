import asyncio

from langchain_core.messages import AIMessage, ToolMessage

from app.core.agent import reflexion_node, should_reflect


async def test_reflexion_logic():
    print("--- Unit Testing Reflexion Logic ---")

    # Scenario 1: Tool Error triggers Reflexion
    print("\n1. Testing Trigger Logic (should_reflect)")
    state_error = {
        "messages": [
            AIMessage(content="", tool_calls=[{"name": "test", "args": {}, "id": "1"}]),
            ToolMessage(content="Error: Database connection failed", tool_call_id="1", name="test"),
        ],
        "retry_count": 0,
    }

    result = should_reflect(state_error)
    print(f"   Input: Tool Error | Retry=0 -> Result: {result}")
    assert result == "reflexion", "Should reflect on error"

    # Scenario 2: Success triggers Agent
    state_success = {
        "messages": [
            AIMessage(content="", tool_calls=[{"name": "test", "args": {}, "id": "1"}]),
            ToolMessage(content="Success: Data retrived", tool_call_id="1", name="test"),
        ]
    }
    result = should_reflect(state_success)
    print(f"   Input: Tool Success         -> Result: {result}")
    assert result == "agent", "Should go to agent on success"

    # Scenario 3: Retry Limit Exceeded
    state_limit = {"messages": [ToolMessage(content="Error: Fail", tool_call_id="1", name="test")], "retry_count": 3}
    result = should_reflect(state_limit)
    print(f"   Input: Tool Error | Retry=3 -> Result: {result}")
    assert result == "agent", "Should give up after 3 retries"

    print("\n2. Testing Reflexion Node Output")
    # Test that it generates a SystemMessage and increments count
    reflexion_out = await reflexion_node(state_error)

    msg_content = reflexion_out["messages"][0].content
    new_count = reflexion_out["retry_count"]

    print(f"   Output Count: {new_count}")
    print(f"   Output Msg: {msg_content[:50]}...")

    assert new_count == 1, "Should increment retry count"
    assert "REFLECTION" in msg_content, "Should contain reflection tag"

    print("\n✅ All Unit Tests Passed")


if __name__ == "__main__":
    asyncio.run(test_reflexion_logic())
