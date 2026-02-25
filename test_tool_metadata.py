from langchain_core.tools import tool


@tool
def dummy_tool():
    """Dummy tool."""
    pass


print(f"Has metadata: {hasattr(dummy_tool, 'metadata')}")
print(f"Metadata value: {dummy_tool.metadata}")
