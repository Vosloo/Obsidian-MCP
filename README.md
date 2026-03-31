# Obsidian MCP

An MCP (Model Context Protocol) server that connects your LLM to your Obsidian vault. Read, write, search, and organize your notes through natural conversation.

Built on top of the [Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin.

## Features

- **Read & write notes** — create, update, append, and delete notes and directories
- **Search** — find notes by filename pattern or full-text search across the vault
- **Batch operations** — read, append, or delete multiple notes in parallel
- **Tree view** — display vault structure with configurable depth
- **Section editing** — update content under a specific heading without rewriting the whole note
- **Frontmatter** — update YAML frontmatter fields (tags, dates, metadata)
- **Daily notes** — retrieve today's daily note or any past date

## Prerequisites

- [Obsidian](https://obsidian.md/) with the **Local REST API** community plugin installed and enabled
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+

## Setup

### 1. Configure the Obsidian plugin

1. Open Obsidian → Settings → Community Plugins
2. Search for **Local REST API**, install and enable it
3. In the plugin settings, copy your **API key** and note the port (default `27123`)

### 2. Install the MCP server

```bash
git clone https://github.com/Vosloo/Obsidian-MCP.git
cd Obsidian-MCP
uv sync
```

### 3. Set environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
OBSIDIAN_API_URL=http://127.0.0.1:27123
OBSIDIAN_API_KEY=your_api_key_here
```

### 4. Test the connection

```bash
uv run obsidian-mcp
```

If the server starts without errors, you're good to go. Press `Ctrl+C` to stop it.

## Connecting to your LLM

### Claude Desktop

Edit your config file:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the server entry (replace the path with your actual project path):

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/Obsidian-MCP",
        "run",
        "obsidian-mcp"
      ],
      "env": {
        "OBSIDIAN_API_URL": "https://127.0.0.1:27124",
        "OBSIDIAN_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

Restart Claude Desktop. The Obsidian tools should appear in the interface.

### Claude Code (CLI)

Add to your `.claude/settings.json` or run:

```bash
claude mcp add obsidian -- uv --directory /absolute/path/to/Obsidian-MCP run obsidian-mcp
```

Set the environment variables in your shell or `.env` file before launching.

### Other MCP clients

Any client that supports the [Model Context Protocol](https://modelcontextprotocol.io/) can connect. Point it at:

```
uv --directory /path/to/Obsidian-MCP run obsidian-mcp
```

The server communicates over **stdio**.

## Available tools

| Tool | Description |
|------|-------------|
| `search_by_filename` | Find notes by filename pattern (wildcards supported) |
| `search_in_note` | Search text within a specific note |
| `search_in_directory` | Search text across all notes in a directory |
| `read_note` | Read a note as structured JSON with metadata |
| `read_note_markdown` | Read a note as raw markdown |
| `get_daily_note` | Get today's or a specific date's daily note |
| `create_note` | Create a new note or overwrite an existing one |
| `append_to_note` | Append content to an existing note |
| `update_section` | Update content under a specific heading |
| `update_frontmatter` | Update a frontmatter field |
| `delete_note` | Delete a note |
| `list_vault_files` | List all files in the vault root |
| `list_directory` | List contents of a specific directory |
| `create_directory` | Create a new directory |
| `delete_directory` | Recursively delete a directory |
| `batch_read_notes` | Read multiple notes in parallel |
| `batch_append_to_notes` | Append to multiple notes in parallel |
| `batch_delete_notes` | Delete multiple notes at once |
| `tree_view` | Display directory structure as a tree |
| `open_note_in_obsidian` | Open a note in the Obsidian UI |
| `get_vault_info` | Get vault name, path, and API status |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `OBSIDIAN_API_KEY must be set` | Create a `.env` file with your API key, then restart |
| Connection refused | Make sure Obsidian is running and the Local REST API plugin is enabled |
| Module not found | Run `uv sync` to install dependencies |
| Tools not showing in Claude | Check that the path in your config is absolute and uses forward slashes |

## License

MIT
