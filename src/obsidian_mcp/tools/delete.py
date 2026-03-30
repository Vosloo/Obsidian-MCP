"""Delete tools for Obsidian vault."""

from mcp.types import Tool


def get_delete_tools() -> list[Tool]:
    """Return delete-related MCP tools."""
    return [
        Tool(
            name="delete_note",
            description="Permanently delete a note from the vault. WARNING: This action cannot be undone. The note will be moved to your system trash/recycle bin if configured in Obsidian settings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note relative to vault root (e.g., 'NPCs/OldCharacter.md')",
                    },
                },
                "required": ["path"],
            },
        ),
    ]


async def handle_delete_tool(name: str, arguments: dict, client) -> str:
    """Handle delete tool execution."""
    if name == "delete_note":
        await client.delete_note(path=arguments["path"])
        return f"Note deleted: {arguments['path']}"

    raise ValueError(f"Unknown delete tool: {name}")
