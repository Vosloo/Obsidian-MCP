"""Read tools for Obsidian vault."""

from mcp.types import Tool


def get_read_tools() -> list[Tool]:
    """Return read-related MCP tools."""
    return [
        Tool(
            name="read_note",
            description="Read the full content of a note including frontmatter, tags, and metadata. Returns structured JSON with all note information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note relative to vault root (e.g., 'NPCs/Gandor.md' or 'Sessions/Session-01.md')",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="read_note_markdown",
            description="Read a note as raw markdown text without metadata parsing. Use this when you need the exact markdown formatting, or when you want to see the raw frontmatter YAML. Use 'read_note' instead if you want structured JSON data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note relative to vault root (e.g., 'NPCs/Gandor.md')",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="get_daily_note",
            description="Get a daily note by date. If no date is provided, returns today's daily note.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Year (e.g., 2026)",
                    },
                    "month": {
                        "type": "integer",
                        "description": "Month (1-12)",
                    },
                    "day": {
                        "type": "integer",
                        "description": "Day (1-31)",
                    },
                },
            },
        ),
    ]


async def handle_read_tool(name: str, arguments: dict, client) -> str:
    """Handle read tool execution."""
    if name == "read_note":
        note = await client.get_note(path=arguments["path"], as_json=True)
        return str(note)

    elif name == "read_note_markdown":
        content = await client.get_note(path=arguments["path"], as_json=False)
        return str(content)

    elif name == "get_daily_note":
        note = await client.get_periodic_note(
            period="daily",
            year=arguments.get("year"),
            month=arguments.get("month"),
            day=arguments.get("day"),
            as_json=True,
        )
        return str(note)

    raise ValueError(f"Unknown read tool: {name}")
