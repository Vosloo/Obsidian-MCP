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
        Tool(
            name="read_section",
            description="Read the content of a specific heading section from a note without loading the full file. Use the full heading path as returned by get_document_map (e.g., 'Document Title::Section Name'). Useful for large notes when you only need one section.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note relative to vault root (e.g., 'NPCs/Gandor.md')",
                    },
                    "heading": {
                        "type": "string",
                        "description": "Heading name to read (without # symbols, e.g., 'Combat History')",
                    },
                },
                "required": ["path", "heading"],
            },
        ),
        Tool(
            name="get_document_map",
            description="Get a structural overview of a note: all headings with their hierarchy, block reference IDs, and frontmatter field names. Use this before targeted edits to discover exact heading names and note structure without reading all the content.",
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

    elif name == "read_section":
        content = await client.get_section(
            path=arguments["path"],
            heading=arguments["heading"],
        )
        return str(content)

    elif name == "get_document_map":
        doc_map = await client.get_document_map(path=arguments["path"])
        return _format_document_map(doc_map)

    raise ValueError(f"Unknown read tool: {name}")


def _format_document_map(doc_map: dict) -> str:
    """Format a document map response as readable text."""
    lines = []

    headings = doc_map.get("headings", [])
    if headings:
        lines.append("Headings:")
        _collect_headings(headings, lines)

    blocks = doc_map.get("blocks", [])
    if blocks:
        lines.append("\nBlock references:")
        for b in blocks:
            bid = b if isinstance(b, str) else b.get("id", str(b))
            lines.append(f"  ^{bid}")

    frontmatter = doc_map.get("frontmatterFields", [])
    if frontmatter:
        lines.append("\nFrontmatter fields:")
        for f in frontmatter:
            fname = f if isinstance(f, str) else f.get("key", str(f))
            lines.append(f"  {fname}")

    return "\n".join(lines) if lines else str(doc_map)


def _collect_headings(headings: list, lines: list, depth: int = 0) -> None:
    """Recursively format headings into lines."""
    for h in headings:
        if isinstance(h, str):
            lines.append("  " * depth + f"- {h}")
        elif isinstance(h, dict):
            text = h.get("heading", h.get("text", str(h)))
            level = h.get("level", depth + 1)
            indent = "  " * (level - 1)
            lines.append(f"{indent}- {text}")
            children = h.get("children", [])
            if children:
                _collect_headings(children, lines, depth + 1)
