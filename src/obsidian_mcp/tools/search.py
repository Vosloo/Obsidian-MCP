"""Search tools for Obsidian vault."""

import fnmatch
from typing import Any

from mcp.types import Tool


def get_search_tools() -> list[Tool]:
    """Return search-related MCP tools."""
    return [
        # Directory listing tools (these work perfectly)
        Tool(
            name="list_vault_files",
            description="List all files and directories in the vault root directory. Useful for discovering the vault structure and finding top-level folders.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="list_directory",
            description="List all files and subdirectories in a specific directory. Use this to explore folder contents and discover notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to vault root (e.g., 'NPCs', '0-Campaign/Sessions')",
                    },
                },
                "required": ["path"],
            },
        ),
        # Filename-based search (fast and reliable)
        Tool(
            name="search_by_filename",
            description="Search for notes by filename/path pattern across the entire vault (when no directory given) or within a specific directory. Uses wildcard patterns like 'NPC*' or '*dragon*'. When no directory is specified, searches all notes vault-wide via the API.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Filename pattern to search for (supports wildcards like 'session*', '*npc*', etc.)",
                    },
                    "directory": {
                        "type": "string",
                        "description": "Optional: directory to search in (e.g., 'NPCs', '0-Campaign'). If not provided, searches entire vault.",
                    },
                },
                "required": ["pattern"],
            },
        ),
        # Content-based search (client-side, works around API bugs)
        Tool(
            name="search_in_note",
            description="Search for text within a specific note. Faster than vault-wide search. Use this when you know which note to search in.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to note to search in",
                    },
                    "query": {
                        "type": "string",
                        "description": "Text to search for (e.g., 'ability score', 'dragon', 'session 5')",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether search should be case-sensitive (default: false)",
                        "default": False,
                    },
                },
                "required": ["path", "query"],
            },
        ),
        Tool(
            name="search_in_directory",
            description="Search for text across all notes in a specific directory. More efficient than vault-wide search.",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to search in (e.g., 'NPCs', '0-Campaign/Sessions')",
                    },
                    "query": {
                        "type": "string",
                        "description": "Text to search for (e.g., 'ability score', 'dragon', 'session 5')",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether search should be case-sensitive (default: false)",
                        "default": False,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["directory", "query"],
            },
        ),
    ]


async def _search_in_content(content: str, query: str, case_sensitive: bool = False) -> list[dict[str, Any]]:
    """Search for query in content and return matches with context."""
    query_lower = query if case_sensitive else query.lower()

    matches = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        search_line = line if case_sensitive else line.lower()
        if query_lower in search_line:
            # Find position in line
            pos = search_line.index(query_lower)

            # Get context (50 chars before and after)
            context_start = max(0, pos - 50)
            context_end = min(len(line), pos + len(query) + 50)
            context = line[context_start:context_end]

            matches.append(
                {
                    "line": line_num,
                    "content": line.strip(),
                    "context": context,
                    "position": pos,
                }
            )

    return matches


async def handle_search_tool(name: str, arguments: dict, client) -> str:
    """Handle search tool execution."""
    # Directory listing
    if name == "list_vault_files":
        results = await client.list_vault_root()
        return str(results)

    elif name == "list_directory":
        results = await client.list_directory(path=arguments["path"])
        return str(results)

    # Filename search
    elif name == "search_by_filename":
        pattern = arguments["pattern"]
        directory = arguments.get("directory", "")

        if directory:
            # Scoped search: list directory and filter client-side
            listing = await client.list_directory(directory)
            files = listing.get("files", [])
            matching_files = [f for f in files if fnmatch.fnmatch(f.lower(), pattern.lower())]
        else:
            # Vault-wide search: fetch all note paths via a JsonLogic tautology,
            # then filter client-side with fnmatch.
            # Note: JsonLogic glob/regexp operators do not work against the path
            # variable in practice, so client-side filtering is required.
            # Pattern is matched against the filename portion of the path only.
            try:
                results = await client.search_jsonlogic({"==": [1, 1]})
                all_paths = [r["filename"] for r in results]
                matching_files = [
                    p for p in all_paths
                    if fnmatch.fnmatch(p.split("/")[-1].lower(), pattern.lower())
                ]
            except Exception as e:
                return f"Vault-wide search failed: {e}"

        if not matching_files:
            return f"No files found matching pattern '{pattern}'"

        result = {
            "pattern": pattern,
            "directory": directory or "entire vault",
            "matches": len(matching_files),
            "files": matching_files[:50],  # Limit to 50 results
        }

        if len(matching_files) > 50:
            result["note"] = f"Showing first 50 of {len(matching_files)} matches"

        return str(result)

    # Content search in single note
    elif name == "search_in_note":
        path = arguments["path"]
        query = arguments["query"]
        case_sensitive = arguments.get("case_sensitive", False)

        # Read the note
        content = await client.get_note(path, as_json=False)

        # Title match
        title = path.split("/")[-1]
        if title.endswith(".md"):
            title = title[:-3]
        search_title = title if case_sensitive else title.lower()
        query_cmp = query if case_sensitive else query.lower()
        title_matches = (
            [{"line": 0, "type": "title", "content": title,
              "context": f"{title} (note title)", "position": 0}]
            if query_cmp in search_title else []
        )

        # Search in content
        matches = title_matches + await _search_in_content(content, query, case_sensitive)

        if not matches:
            return f"No matches found for '{query}' in {path}"

        result = {
            "path": path,
            "query": query,
            "total_matches": len(matches),
            "matches": matches[:20],  # Limit to 20 matches
        }

        if len(matches) > 20:
            result["note"] = f"Showing first 20 of {len(matches)} matches"

        return str(result)

    # Content search in directory
    elif name == "search_in_directory":
        directory = arguments["directory"]
        query = arguments["query"]
        case_sensitive = arguments.get("case_sensitive", False)
        max_results = arguments.get("max_results", 20)

        # List files in directory
        listing = await client.list_directory(directory)
        files = listing.get("files", [])

        # Filter to only .md files
        md_files = [f for f in files if f.endswith(".md") or "/" in f]

        results = []
        total_matches = 0
        files_searched = 0

        # Search in each file
        for file_path in md_files:
            if len(results) >= max_results:
                break

            try:
                # Construct full path
                full_path = f"{directory}/{file_path}" if directory else file_path

                # Read content
                content = await client.get_note(full_path, as_json=False)
                files_searched += 1

                # Title match
                title = file_path.split("/")[-1]
                if title.endswith(".md"):
                    title = title[:-3]
                search_title = title if case_sensitive else title.lower()
                query_cmp = query if case_sensitive else query.lower()
                title_matches = (
                    [{"line": 0, "type": "title", "content": title,
                      "context": f"{title} (note title)", "position": 0}]
                    if query_cmp in search_title else []
                )

                # Search in content
                matches = title_matches + await _search_in_content(content, query, case_sensitive)

                if matches:
                    total_matches += len(matches)
                    results.append(
                        {
                            "file": full_path,
                            "matches": len(matches),
                            "preview": matches[0],  # Show first match as preview
                        }
                    )

            except Exception:
                # Skip files that can't be read
                continue

        if not results:
            return f"No matches found for '{query}' in directory '{directory}'"

        result = {
            "directory": directory,
            "query": query,
            "files_searched": files_searched,
            "files_with_matches": len(results),
            "total_matches": total_matches,
            "results": results,
        }

        return str(result)

    raise ValueError(f"Unknown search tool: {name}")
