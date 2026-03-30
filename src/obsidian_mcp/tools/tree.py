"""Tree view tool for Obsidian vault."""

import os

from mcp.types import Tool


def _get_default_exclude_dirs() -> set[str]:
    """Read TREE_VIEW_EXCLUDE_DIRS env var, return set of dir names to exclude."""
    raw = os.getenv("TREE_VIEW_EXCLUDE_DIRS", "")
    return {d.strip() for d in raw.split(",") if d.strip()}


def get_tree_tools() -> list[Tool]:
    """Return tree-related MCP tools."""
    return [
        Tool(
            name="tree_view",
            description="Display directory structure as a tree with configurable depth. "
            "Shows nested files and folders with visual hierarchy. "
            "Useful for understanding vault organization at a glance. "
            "Directories configured in TREE_VIEW_EXCLUDE_DIRS env var are shown but not expanded (marked [excluded]) — "
            "to explore an excluded directory, call this tool again with that directory as the 'path' argument.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to display tree for (e.g., 'Notes', 'Projects/2024'). "
                        "Empty string for vault root.",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse (default: 3). Use -1 for unlimited depth.",
                    },
                    "exclude_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Directory names to exclude from expansion (e.g. ['1-Mechanics', 'Archive']). "
                        "Excluded dirs are shown in the tree but not expanded. "
                        "Merged with TREE_VIEW_EXCLUDE_DIRS env var.",
                    },
                },
                "required": [],
            },
        ),
    ]


async def handle_tree_tool(name: str, arguments: dict, client) -> str:
    """Handle tree tool execution."""
    if name == "tree_view":
        path = arguments.get("path", "")
        max_depth = arguments.get("max_depth", 3)
        extra_exclude = set(arguments.get("exclude_dirs") or [])
        exclude_dirs = _get_default_exclude_dirs() | extra_exclude

        lines = []
        root_name = path if path else "/"
        lines.append(root_name)

        await _build_tree(client, path, max_depth, 0, "", lines, exclude_dirs)

        return "\n".join(lines)

    raise ValueError(f"Unknown tree tool: {name}")


async def _build_tree(
    client,
    path: str,
    max_depth: int,
    current_depth: int,
    prefix: str,
    lines: list[str],
    exclude_dirs: set[str],
) -> None:
    """Recursively build tree structure.

    Args:
        client: ObsidianClient instance
        path: Current directory path
        max_depth: Maximum depth (-1 for unlimited)
        current_depth: Current recursion depth
        prefix: Line prefix for indentation
        lines: Output lines list (mutated)
        exclude_dirs: Directory names to skip expanding
    """
    # Check depth limit
    if max_depth != -1 and current_depth >= max_depth:
        return

    # Get directory contents
    try:
        if path:
            listing = await client.list_directory(path)
        else:
            listing = await client.list_vault_root()
    except Exception:
        return

    files = listing.get("files", [])
    if not files:
        return

    # Separate directories and files, sort each group
    dirs = sorted([f for f in files if f.endswith("/")])
    regular_files = sorted([f for f in files if not f.endswith("/")])

    # Directories first, then files
    entries = dirs + regular_files

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "

        lines.append(f"{prefix}{connector}{entry}")

        # Recurse into directories
        if entry.endswith("/"):
            dir_name = entry[:-1]  # strip trailing /
            if dir_name in exclude_dirs:
                lines[-1] += "  [excluded]"
            else:
                new_prefix = prefix + ("    " if is_last else "│   ")
                subdir_path = f"{path}/{dir_name}" if path else dir_name
                await _build_tree(
                    client, subdir_path, max_depth, current_depth + 1, new_prefix, lines, exclude_dirs
                )
