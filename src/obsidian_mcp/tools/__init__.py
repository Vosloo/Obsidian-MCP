"""Tools package for Obsidian MCP operations."""

from .batch import get_batch_tools, handle_batch_tool
from .delete import get_delete_tools, handle_delete_tool
from .directory import get_directory_tools, handle_directory_tool
from .read import get_read_tools, handle_read_tool
from .search import get_search_tools, handle_search_tool
from .tree import get_tree_tools, handle_tree_tool
from .utility import get_utility_tools, handle_utility_tool
from .write import get_write_tools, handle_write_tool

__all__ = [
    "get_search_tools",
    "get_read_tools",
    "get_write_tools",
    "get_delete_tools",
    "get_batch_tools",
    "get_tree_tools",
    "get_utility_tools",
    "handle_search_tool",
    "handle_read_tool",
    "handle_write_tool",
    "handle_delete_tool",
    "handle_batch_tool",
    "handle_tree_tool",
    "handle_utility_tool",
]


def get_all_tools():
    """Get all available MCP tools."""
    return (
        get_search_tools()
        + get_read_tools()
        + get_write_tools()
        + get_delete_tools()
        + get_directory_tools()
        + get_batch_tools()
        + get_tree_tools()
        + get_utility_tools()
    )


async def handle_tool_call(name: str, arguments: dict, client):
    """Route tool call to appropriate handler."""
    # Try each handler
    handlers = [
        handle_search_tool,
        handle_read_tool,
        handle_write_tool,
        handle_delete_tool,
        handle_directory_tool,
        handle_batch_tool,
        handle_tree_tool,
        handle_utility_tool,
    ]

    for handler in handlers:
        try:
            return await handler(name, arguments, client)
        except ValueError:
            continue

    raise ValueError(f"Unknown tool: {name}")
