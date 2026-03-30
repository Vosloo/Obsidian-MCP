"""CLI-powered tools using the official Obsidian CLI."""

import json
import os

from mcp.types import Tool


def _get_default_exclude_dirs() -> list[str]:
    """Read TREE_VIEW_EXCLUDE_DIRS env var and return as a list of path prefixes.

    Reuses the same env var as tree_view so that vault-wide exclusions (e.g. large
    read-only rule compendiums) are respected consistently across all tools.
    """
    raw = os.getenv("TREE_VIEW_EXCLUDE_DIRS", "")
    return [d.strip() for d in raw.split(",") if d.strip()]

_NOT_AVAILABLE = (
    "Obsidian CLI not available. Install Obsidian 1.12+ and ensure "
    "the 'obsidian' binary is on your PATH."
)


def _extract_json(text: str) -> str | None:
    """Find and return the JSON portion of CLI stdout.

    The Obsidian CLI sometimes prints informational messages (e.g. installer
    update notices) to stdout before the actual JSON payload. This strips any
    leading log lines by seeking to the first '[' or '{' character.
    """
    for ch in ("[", "{"):
        idx = text.find(ch)
        if idx != -1:
            return text[idx:]
    return None


def _parse_sources(raw: str | list | None) -> list[str]:
    """Normalise the 'sources' field from the CLI.

    The CLI returns sources as:
    - A comma-and-space-separated string for multiple files:
      "_mcp_test/note-a.md, _mcp_test/note-b.md"
    - A plain string for a single file: "_mcp_test/note-b.md"
    - Or a list (future-proofing).
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [s.strip() for s in raw.split(",") if s.strip()]


def _in_dir(source: str, directory: str) -> bool:
    """Return True if source path is inside directory (slash-normalised)."""
    prefix = directory.rstrip("/\\")
    return source.startswith(prefix + "/") or source.startswith(prefix + "\\")


def get_cli_tools() -> list[Tool]:
    """Return CLI-backed MCP tool definitions."""
    return [
        Tool(
            name="get_tags",
            description=(
                "List all tags used across the vault with their occurrence counts, "
                "sorted by most-used first. Useful for understanding how the vault is "
                "categorised or finding tag inconsistencies (e.g. similar tags with "
                "different names). Use 'path' to limit results to a single note."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Optional: vault-relative path to a single note "
                            "(e.g. 'NPCs/Gandor.md'). Omit to list tags vault-wide."
                        ),
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_unresolved_links",
            description=(
                "Find all unresolved (broken) wikilinks in the vault — [[links]] that "
                "point to notes that do not exist. Each result shows the missing note "
                "name, how many times it is referenced, and which files contain the "
                "reference. Use 'directory' to scope the search to a specific folder, "
                "or 'exclude_dirs' to skip large directories such as rule compendiums "
                "that are known to contain many intentional stubs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": (
                            "Optional: only return unresolved links whose source files "
                            "are inside this directory (e.g. '0-Campaign/Sessions'). "
                            "At least one source must be inside the directory for the "
                            "link to be included."
                        ),
                    },
                    "exclude_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional: skip entries where every source file is inside "
                            "one of these directories. Merged with the "
                            "TREE_VIEW_EXCLUDE_DIRS environment variable, so dirs "
                            "already excluded globally need not be repeated "
                            "(e.g. ['Templates'] if 1-Mechanics is already in the env var)."
                        ),
                    },
                },
                "required": [],
            },
        ),
    ]


async def handle_cli_tool(name: str, arguments: dict, cli) -> str:
    """Handle CLI tool execution."""
    if name == "get_tags":
        if not cli.available:
            return _NOT_AVAILABLE

        args = ["tags", "counts", "sort=count", "format=json"]
        if path := arguments.get("path"):
            args.append(f"path={path}")

        result = await cli.run(*args)
        if not result.ok:
            return f"Error running 'obsidian tags': {result.stderr or result.stdout}"

        json_text = _extract_json(result.stdout)
        try:
            data = json.loads(json_text) if json_text else None
        except json.JSONDecodeError:
            data = None

        if data is None:
            return result.stdout or "No tags found."
        if not data:
            return "No tags found."

        lines = [f"{entry['tag']}: {int(entry['count'])}" for entry in data]
        return "\n".join(lines)

    if name == "get_unresolved_links":
        if not cli.available:
            return _NOT_AVAILABLE

        result = await cli.run("unresolved", "counts", "verbose", "format=json")
        if not result.ok:
            return f"Error running 'obsidian unresolved': {result.stderr or result.stdout}"

        json_text = _extract_json(result.stdout)
        try:
            data = json.loads(json_text) if json_text else None
        except json.JSONDecodeError:
            data = None

        if data is None:
            return result.stdout or "No unresolved links found."
        if not data:
            return "No unresolved links found."

        directory: str = arguments.get("directory", "").rstrip("/\\")
        exclude_prefixes: list[str] = [
            d.rstrip("/\\")
            for d in (_get_default_exclude_dirs() + (arguments.get("exclude_dirs") or []))
        ]

        lines = []
        for entry in data:
            if not isinstance(entry, dict):
                if not directory and not exclude_prefixes:
                    lines.append(f"[[{entry}]]")
                continue

            link = entry.get("link", "?")
            raw_count = entry.get("count")
            count = int(raw_count) if raw_count is not None else None
            sources = _parse_sources(entry.get("sources"))

            # Include filter: at least one source must be inside `directory`
            if directory and not any(_in_dir(s, directory) for s in sources):
                continue

            # Exclude filter: skip if every source is inside an excluded dir
            if exclude_prefixes and sources and all(
                any(_in_dir(s, p) for p in exclude_prefixes) for s in sources
            ):
                continue

            line = f"[[{link}]]"
            if count is not None:
                line += f" ({count} reference{'s' if count != 1 else ''})"
            if sources:
                line += f" — in: {', '.join(sources)}"
            lines.append(line)

        if not lines:
            return "No unresolved links found."
        return "\n".join(lines)

    raise ValueError(f"Unknown CLI tool: {name}")
