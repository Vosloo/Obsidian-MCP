"""Utility tools for Obsidian vault."""

from mcp.types import Tool


def get_utility_tools() -> list[Tool]:
    """Return utility MCP tools."""
    return [
        Tool(
            name="open_note_in_obsidian",
            description="Open a note in the Obsidian user interface. Useful for showing the user a note you've just created or modified.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note relative to vault root (e.g., 'NPCs/NewNPC.md')",
                    },
                    "new_pane": {
                        "type": "boolean",
                        "description": "Open in a new pane instead of current pane (default: false)",
                        "default": False,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="get_vault_info",
            description="Get information about the vault (name, path, REST API version) and verify the API connection is working. Use this for troubleshooting connection issues.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


async def handle_utility_tool(name: str, arguments: dict, client) -> str:
    """Handle utility tool execution."""
    if name == "open_note_in_obsidian":
        await client.open_note(path=arguments["path"], new_leaf=arguments.get("new_pane", False))
        return f"Opened in Obsidian: {arguments['path']}"

    elif name == "get_vault_info":
        info = await client.get_vault_info()
        return str(info)

    raise ValueError(f"Unknown utility tool: {name}")
