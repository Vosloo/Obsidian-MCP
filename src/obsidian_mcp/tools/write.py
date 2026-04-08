"""Write tools for Obsidian vault."""

from mcp.types import Tool


def get_write_tools() -> list[Tool]:
    """Return write-related MCP tools."""
    return [
        Tool(
            name="create_note",
            description="Create a new note or completely overwrite an existing note. Use this to create new NPCs, locations, session notes, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note relative to vault root (e.g., 'NPCs/NewCharacter.md')",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full markdown content including frontmatter if desired. Use actual newline characters (\\n), not escaped strings. Multi-line content should be a proper multi-line string.",
                    },
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="append_to_note",
            description="Append content to the end of an existing note. Great for adding to session logs or updating character histories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note relative to vault root",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to append. Use actual newline characters (\\n), not escaped strings. Multi-line content should be a proper multi-line string.",
                    },
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="update_section",
            description="Update content under a specific heading in a note. Use the full heading path as returned by get_document_map (e.g., 'Document Title::Section Name' or just 'Section Name' for top-level headings without a parent H1).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note relative to vault root",
                    },
                    "heading": {
                        "type": "string",
                        "description": "Heading path as shown by get_document_map, without # symbols (e.g., 'Document Title::Section Name' or 'Section Name')",
                    },
                    "content": {
                        "type": "string",
                        "description": "New content for the section. Use actual newline characters (\\n), not escaped strings. Multi-line content should be a proper multi-line string.",
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["replace", "append", "prepend"],
                        "description": "How to update the section content (default: replace)",
                        "default": "replace",
                    },
                    "create_if_missing": {
                        "type": "boolean",
                        "description": "Create the heading section if it doesn't exist (default: false)",
                        "default": False,
                    },
                },
                "required": ["path", "heading", "content"],
            },
        ),
        Tool(
            name="move_note",
            description="Move a note to a different directory, preserving its filename. "
            "The note's content is unchanged and standard [[WikiLinks]] pointing to it "
            "continue to work (Obsidian resolves links by filename, not path). "
            "Note: path-specific links like [[old/folder/Note]] will break after moving.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_path": {
                        "type": "string",
                        "description": "Current path of the note (e.g., 'NPCs/Gandor.md')",
                    },
                    "destination_dir": {
                        "type": "string",
                        "description": "Target directory to move the note into (e.g., 'Archive' or 'Archive/2024'). "
                        "The filename is preserved automatically.",
                    },
                },
                "required": ["source_path", "destination_dir"],
            },
        ),
        Tool(
            name="update_frontmatter",
            description="Update a frontmatter field in a note. Useful for updating character stats, dates, tags, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note relative to vault root",
                    },
                    "key": {
                        "type": "string",
                        "description": "Frontmatter key to update",
                    },
                    "value": {
                        "type": "string",
                        "description": "New value for the key",
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["replace", "append", "prepend"],
                        "description": "How to update the field (default: replace)",
                        "default": "replace",
                    },
                },
                "required": ["path", "key", "value"],
            },
        ),
    ]


def _find_section(lines: list[str], heading: str) -> tuple[int, int] | None:
    """Find the start and end line indices of a section.

    Returns:
        Tuple of (start_line, end_line) or None if not found
        start_line is the line with the heading
        end_line is the line before the next heading or end of file
    """
    heading_level = None
    start_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check if this is a heading
        if stripped.startswith("#"):
            # Extract heading text (remove # symbols and strip)
            heading_text = stripped.lstrip("#").strip()

            if heading_text == heading:
                # Found our heading
                heading_level = len(stripped) - len(stripped.lstrip("#"))
                start_idx = i
                continue

            # If we found our heading and now see another heading at same or higher level, we're done.
            # Level-1 headings (document title) terminate at any subsequent heading.
            if start_idx is not None and heading_level is not None:
                current_level = len(stripped) - len(stripped.lstrip("#"))
                if current_level <= heading_level or heading_level == 1:
                    return (start_idx, i - 1)

    # If we found the heading but no ending, it goes to end of file
    if start_idx is not None:
        return (start_idx, len(lines) - 1)

    return None


async def handle_write_tool(name: str, arguments: dict, client, cli=None) -> str:
    """Handle write tool execution."""
    if name == "create_note":
        await client.create_note(path=arguments["path"], content=arguments["content"])
        return f"Note created: {arguments['path']}"

    elif name == "append_to_note":
        await client.append_to_note(path=arguments["path"], content=arguments["content"])
        return f"Content appended to: {arguments['path']}"

    elif name == "update_section":
        await client.update_section(
            path=arguments["path"],
            heading=arguments["heading"],
            content=arguments["content"],
            operation=arguments.get("operation", "replace"),
            create_if_missing=arguments.get("create_if_missing", False),
        )
        return f"Section '{arguments['heading']}' updated in: {arguments['path']}"

    elif name == "move_note":
        source_path = arguments["source_path"]
        destination_dir = arguments["destination_dir"].rstrip("/")

        # Preserve the original filename
        filename = source_path.split("/")[-1]
        destination_path = f"{destination_dir}/{filename}"

        # Try the Obsidian CLI first — it performs a native move that preserves
        # timestamps and triggers Obsidian's "Automatically update internal links".
        # 'to=' accepts the destination directory; the CLI preserves the filename.
        if cli is not None and cli.available:
            result = await cli.run("move", f"path={source_path}", f"to={destination_dir}")
            if result.ok:
                return f"Note moved: '{source_path}' → '{destination_path}'"
            # CLI failed (e.g. destination dir doesn't exist) — fall through below

        # Fallback: read → create → delete via REST API
        # Step 1: Read source content
        try:
            content = await client.get_note(source_path, as_json=False)
        except Exception as e:
            return f"Error reading source note '{source_path}': {e}"

        # Step 2: Create at destination
        try:
            await client.create_note(destination_path, content)
        except Exception as e:
            return f"Error creating note at '{destination_path}': {e}"

        # Step 3: Delete source (note already safely exists at destination)
        try:
            await client.delete_note(source_path)
        except Exception as e:
            return (
                f"Warning: Note was copied to '{destination_path}' but the original "
                f"at '{source_path}' could not be deleted: {e}. "
                f"Please delete it manually."
            )

        return f"Note moved: '{source_path}' → '{destination_path}'"

    elif name == "update_frontmatter":
        await client.update_frontmatter(
            path=arguments["path"],
            key=arguments["key"],
            value=arguments["value"],
            operation=arguments.get("operation", "replace"),
        )
        return f"Frontmatter '{arguments['key']}' updated in: {arguments['path']}"

    raise ValueError(f"Unknown write tool: {name}")
