# Quick Setup Guide

## Step 1: Install Obsidian Local REST API Plugin

1. Open Obsidian
2. Go to Settings → Community Plugins
3. Click "Browse" and search for "Local REST API"
4. Install and Enable the plugin
5. Click on the plugin settings
6. **Copy your API Key** (you'll need this in Step 3)
7. Note the API port (default is `27123`)

## Step 2 (Optional): Enable the Obsidian CLI

Some tools (`get_tags`, `get_unresolved_links`) and an enhanced version of `move_note` rely on the Obsidian CLI, which ships with **Obsidian 1.12+** but must be explicitly enabled:

1. Open Obsidian
2. Go to **Settings → General → Advanced**
3. Toggle on **"Command line interface"**

Without this, `get_tags` and `get_unresolved_links` will report that the CLI is unavailable, and `move_note` will fall back to a copy-then-delete approach (which doesn't preserve timestamps or trigger Obsidian's automatic link updates).

## Step 3: Install the MCP Server

```bash
# Navigate to the project directory
cd Obsidian-MCP

# Install dependencies using uv
uv sync

# This will create a .venv folder with all dependencies
```

## Step 4: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env
```

Update these values in `.env`:
```bash
OBSIDIAN_API_URL=https://127.0.0.1:27124
OBSIDIAN_API_KEY=paste_your_api_key_here
```

## Step 5: Test the Connection

```bash
# Try running the server directly
uv run obsidian-mcp

# You should see the server start up
# Press Ctrl+C to stop it
```

## Step 6: Configure Claude Desktop

### Windows
Edit: `%APPDATA%\Claude\claude_desktop_config.json`

### macOS
Edit: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this configuration (replace the path with your actual absolute path):

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

**Important**:
- Use forward slashes `/` in the path, even on Windows
- Use the absolute path to the project directory
- Replace `your_api_key_here` with your actual API key

## Step 7 (Alternative): Configure Claude Code CLI

If you use Claude Code instead of Claude Desktop, run:

```bash
claude mcp add obsidian -- uv --directory /absolute/path/to/Obsidian-MCP run obsidian-mcp
```

Then set the environment variables in your shell or `.env` file before launching Claude Code.

## Step 8: Restart Claude Desktop

1. Completely quit Claude Desktop
2. Reopen Claude Desktop
3. You should see the Obsidian tools available in the interface

## Troubleshooting

### "OBSIDIAN_API_KEY must be set"
- Make sure you created the `.env` file (not `.env.example`)
- Check that you pasted the API key correctly
- Restart Claude Desktop after making changes

### "Connection refused" or "Cannot connect"
- Make sure Obsidian is running
- Make sure the Local REST API plugin is enabled
- Check that the port in `.env` matches the plugin settings (default: 27124 for HTTPS)

### "Module not found" errors
- Run `uv sync` again in the project directory
- Make sure the virtual environment was created (`.venv` folder should exist)

### Tools not showing in Claude Desktop
- Check that the path in `claude_desktop_config.json` is correct and absolute
- Use forward slashes in the path
- Restart Claude Desktop completely
- Check Claude Desktop logs for errors

## Next Steps

Once everything is working:

1. Try asking Claude: "Search my Obsidian vault for notes about dragons"
2. Ask: "Create a new NPC character sheet for a dwarf blacksmith"
3. Ask: "Show me today's daily note"
4. Ask: "List all my session notes"

Enjoy your AI-powered Obsidian workflow!
