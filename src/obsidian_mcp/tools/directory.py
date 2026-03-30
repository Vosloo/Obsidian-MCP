"""Directory management tools for Obsidian vault."""

from mcp.types import Tool


def get_directory_tools() -> list[Tool]:
    """Return directory management MCP tools."""
    return [
        Tool(
            name="create_directory",
            description="Create a new directory in the vault. Parent directories are created automatically if they don't exist. Useful for organizing notes into new folder structures.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to vault root (e.g., 'Campaigns/2024', 'NPCs/Villains')",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="delete_directory",
            description="Recursively delete a directory and all its contents (files and subdirectories). WARNING: This action cannot be undone and will delete ALL files within the directory!",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to vault root to delete (e.g., 'OldCampaign', 'Archive/2023')",
                    },
                },
                "required": ["path"],
            },
        ),
    ]


async def handle_directory_tool(name: str, arguments: dict, client) -> str:
    """Handle directory tool execution."""
    if name == "create_directory":
        path = arguments["path"]

        # Create directory by creating a placeholder file, then deleting it
        # This works because Obsidian creates directories automatically when creating files
        placeholder_path = f"{path}/.placeholder"

        try:
            # Create placeholder file
            await client.create_note(placeholder_path, "")

            # Delete placeholder file (directory remains)
            # Note: In Obsidian, empty directories might not persist, but this ensures
            # the directory is created for subsequent file operations
            await client.delete_note(placeholder_path)

            return f"Directory created: {path}"
        except Exception as e:
            return f"Failed to create directory '{path}': {str(e)}"

    elif name == "delete_directory":
        path = arguments["path"]

        try:
            # List all files in the directory
            listing = await client.list_directory(path)
            files = listing.get("files", [])

            if not files:
                return f"Directory '{path}' is empty or doesn't exist"

            # Delete all files (including subdirectories)
            deleted_count = 0
            errors = []

            for file_path in files:
                try:
                    # Remove trailing slash if present (directory listings include it)
                    clean_path = file_path.rstrip("/")
                    full_path = f"{path}/{clean_path}"

                    # If it's a directory (ends with /), recursively delete it
                    if file_path.endswith("/"):
                        # It's a directory, recursively delete
                        await handle_directory_tool("delete_directory", {"path": full_path}, client)
                        deleted_count += 1
                    else:
                        # It's a file, delete it
                        await client.delete_note(full_path)
                        deleted_count += 1

                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")

            result_parts = [f"Deleted {deleted_count} items from '{path}'"]
            if errors:
                result_parts.append(f"Errors: {', '.join(errors[:5])}")  # Show first 5 errors

            return ". ".join(result_parts)

        except Exception as e:
            return f"Failed to delete directory '{path}': {str(e)}"

    raise ValueError(f"Unknown directory tool: {name}")
