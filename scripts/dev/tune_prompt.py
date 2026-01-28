import asyncio
import io
import json
import logging
from contextlib import redirect_stdout

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

# Setup basic logging
logging.basicConfig(level=logging.ERROR)


# --- MOCK TOOLS ---
@tool
def list_entities():
    """List all available devices in Home Assistant."""
    entities = []
    for i in range(800):
        entities.append(
            {"entity_id": f"sensor.temp_{i}", "state": "20.5", "attributes": {"friendly_name": f"Temp Sensor {i}"}}
        )
    entities.append(
        {"entity_id": "light.living_room", "state": "on", "attributes": {"friendly_name": "Living Room Light"}}
    )
    return json.dumps(entities)


@tool
def get_state(entity_id: str):
    """Get the state of a specific entity."""
    return "20.5"


@tool
def python_sandbox(code: str):
    """Executes Python code. Use this to process large data files."""
    print("\n🐍 [Sandbox] Executing Code...")
    try:
        f_capture = io.StringIO()
        with redirect_stdout(f_capture):
            exec(code, {"json": json})
        output = f_capture.getvalue()
        return output if output else "Code executed. (No print output)"
    except Exception as e:
        return f"Error: {e}"


# --- PROMPT ---
EXPERIMENTAL_SYSTEM_PROMPT = """
You are Nexus, an AI operating system.

### AVAILABLE TOOLS
1. `list_entities`: Lists devices.
2. `python_sandbox(code)`: Runs Python code.
3. `get_state(entity_id)`: Gets device state.

### CRITICAL RULES
1. **DATA OVERFLOW**: If a tool returns "Data offloaded to file...",
   you MUST use `python_sandbox` to read that file and filter it.
2. **NO CHATTY CODE**: 
   - DO NOT write Python code in your chat response. 
   - **YOU MUST CALL THE `python_sandbox` TOOL** with the code in the arguments.
3. **ID GUESSING**: Do not guess entity IDs. Find them first.
"""


async def run_test():
    print("--- 🧪 Starting 'Intelligent Proxy' Simulation ---")

    llm = ChatOllama(base_url="http://host.docker.internal:11434", model="qwen2.5:32b", temperature=0)

    tools = [list_entities, get_state, python_sandbox]
    llm_with_tools = llm.bind_tools(tools)

    query = "帮我查一下客厅里所有的灯的状态，我不知道它们的 ID，请先搜索。"
    messages = [SystemMessage(content=EXPERIMENTAL_SYSTEM_PROMPT), HumanMessage(content=query)]

    print(f"\n📝 Query: {query}")
    print(f"🤖 Model: {llm.model}")

    MAX_ITER = 5
    for i in range(MAX_ITER):
        print(f"\n--- 🔄 Step {i + 1} ---")

        try:
            # Use streaming to show progress
            print("🤖 AI Thinking: ", end="", flush=True)
            full_content = ""
            final_tool_calls = []

            async for chunk in llm_with_tools.astream(messages):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
                    full_content += str(chunk.content)
                if chunk.tool_calls:
                    final_tool_calls.extend(chunk.tool_calls)
            print("\n")

            response = AIMessage(content=full_content, tool_calls=final_tool_calls)

            # Qwen Patch: Fix raw JSON output
            if not response.tool_calls and response.content.strip().startswith("{"):
                try:
                    clean_content = response.content.strip()
                    if clean_content.startswith("```json"):
                        clean_content = clean_content[7:-3]
                    data = json.loads(clean_content)
                    if "name" in data:
                        print(f"⚠️ [Patch] Detected raw JSON tool call: {data['name']}")
                        response = AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": data["name"],
                                    "args": data.get("arguments", {}) or data.get("parameters", {}),
                                    "id": "patch_id",
                                }
                            ],
                        )
                except Exception:
                    pass

            print(f"🤖 AI Content: {response.content}")
            print(f"🛠️ Tool Calls: {response.tool_calls}")

            if not response.tool_calls and "Data offloaded" in str(messages[-1].content if messages else ""):
                print("⚠️ Llama missed the cue. Injecting system reminder...")
                messages.append(HumanMessage(content="SYSTEM: STOP EXPLAINING. CALL THE `python_sandbox` TOOL NOW."))
                continue

        except Exception as e:
            print(f"Error invoking LLM: {e}")
            break

        if not response.tool_calls:
            print("🏁 No tools called. Ending.")
            break

        messages.append(response)

        for tool_call in response.tool_calls:
            t_name = tool_call["name"]
            t_args = tool_call["args"]

            if t_name == "list_entities":
                print("⚡ [Middleware] Intercepting list_entities...")
                raw_data = list_entities.invoke(t_args)

                if len(raw_data) > 1000:
                    filename = "large_entities.json"
                    with open(filename, "w") as f:
                        f.write(raw_data)
                    print(f"💾 [Middleware] Data too large ({len(raw_data)} chars). Saved to {filename}")

                    mock_response = (
                        f"SYSTEM_ERROR: OUTPUT_TOO_LARGE ({len(raw_data)} bytes). "
                        f"Data offloaded to file: '{filename}'. "
                        "MANDATORY ACTION: Call `python_sandbox` to read this file and filter it."
                    )
                    messages.append(ToolMessage(tool_call_id=tool_call["id"], content=mock_response, name=t_name))
                else:
                    messages.append(ToolMessage(tool_call_id=tool_call["id"], content=raw_data, name=t_name))

            elif t_name == "python_sandbox":
                print("🐍 [Sandbox] Running code...")
                output = python_sandbox.invoke(t_args)
                print(f"🐍 Output: {output.strip()}")
                messages.append(ToolMessage(tool_call_id=tool_call["id"], content=output, name=t_name))

            else:
                print(f"🔧 [Pass-Through] Calling {t_name}...")
                messages.append(ToolMessage(tool_call_id=tool_call["id"], content="state: on", name=t_name))


if __name__ == "__main__":
    asyncio.run(run_test())
