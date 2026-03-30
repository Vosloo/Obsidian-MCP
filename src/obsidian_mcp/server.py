"""MCP server for Obsidian vault operations."""

import asyncio
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import TextContent, Tool

from .client import ObsidianClient
from .tools import get_all_tools, handle_tool_call

# Load environment variables
load_dotenv()

# Server instance
app = Server("obsidian-mcp")

# Global client instance
client: ObsidianClient | None = None


def get_client() -> ObsidianClient:
    """Get or create the Obsidian client instance."""
    global client
    if client is None:
        client = ObsidianClient()
    return client


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return get_all_tools()


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        client = get_client()
        result = await handle_tool_call(name, arguments, client)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def async_main():
    """Run the MCP server (async entry point)."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Main entry point for the MCP server."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
