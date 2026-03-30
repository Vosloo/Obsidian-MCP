"""Batch operation tools for Obsidian vault."""

import anyio

from mcp.types import Tool


def get_batch_tools() -> list[Tool]:
    """Return batch operation MCP tools."""
    return [
        Tool(
            name="batch_read_notes",
            description="Read multiple notes efficiently in parallel. Returns structured JSON data for each note including frontmatter and metadata. Much faster than calling read_note multiple times.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of note paths to read (e.g., ['NPCs/Character1.md', 'NPCs/Character2.md'])",
                    },
                },
                "required": ["paths"],
            },
        ),
        Tool(
            name="batch_append_to_notes",
            description="Append content to multiple notes in parallel. Useful for updating multiple session notes, NPCs, or locations at once. Much faster than calling append_to_note multiple times.",
            inputSchema={
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["path", "content"],
                        },
                        "description": "List of append operations. Each 'content' field should use actual newline characters (\\n), not escaped strings.",
                    },
                },
                "required": ["operations"],
            },
        ),
        Tool(
            name="batch_delete_notes",
            description="Delete multiple notes at once. WARNING: This action cannot be undone. Notes will be moved to system trash/recycle bin if configured.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of note paths to delete (e.g., ['NPCs/OldNPC1.md', 'NPCs/OldNPC2.md'])",
                    },
                },
                "required": ["paths"],
            },
        ),
    ]


async def _gather_ignoring_errors(*coros) -> list:
    """Run coroutines concurrently, capturing exceptions as result values."""
    results: list = [None] * len(coros)

    async def run(i: int, coro) -> None:
        try:
            results[i] = await coro
        except Exception as e:
            results[i] = e

    async with anyio.create_task_group() as tg:
        for i, coro in enumerate(coros):
            tg.start_soon(run, i, coro)

    return results


async def handle_batch_tool(name: str, arguments: dict, client) -> str:
    """Handle batch tool execution."""
    if name == "batch_read_notes":
        coros = [client.get_note(path=path, as_json=True) for path in arguments["paths"]]
        results = await _gather_ignoring_errors(*coros)
        return str(results)

    elif name == "batch_append_to_notes":
        coros = [
            client.append_to_note(path=op["path"], content=op["content"])
            for op in arguments["operations"]
        ]
        await _gather_ignoring_errors(*coros)
        return f"Appended to {len(arguments['operations'])} notes"

    elif name == "batch_delete_notes":
        coros = [client.delete_note(path=path) for path in arguments["paths"]]
        await _gather_ignoring_errors(*coros)
        return f"Deleted {len(arguments['paths'])} notes"

    raise ValueError(f"Unknown batch tool: {name}")
