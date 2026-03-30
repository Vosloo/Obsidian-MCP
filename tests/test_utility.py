"""Tests for utility tools."""

import pytest

from obsidian_mcp.tools.utility import handle_utility_tool


class TestOpenNoteInObsidian:
    @pytest.mark.anyio
    async def test_opens_note(self, mock_client):
        result = await handle_utility_tool(
            "open_note_in_obsidian", {"path": "note.md"}, mock_client
        )

        mock_client.open_note.assert_awaited_once_with(path="note.md", new_leaf=False)
        assert "note.md" in result

    @pytest.mark.anyio
    async def test_opens_in_new_pane(self, mock_client):
        result = await handle_utility_tool(
            "open_note_in_obsidian", {"path": "note.md", "new_pane": True}, mock_client
        )

        mock_client.open_note.assert_awaited_once_with(path="note.md", new_leaf=True)
        assert "note.md" in result


class TestGetVaultInfo:
    @pytest.mark.anyio
    async def test_returns_info(self, mock_client):
        mock_client.get_vault_info.return_value = {
            "authenticated": True,
            "service": "Obsidian Local REST API",
        }

        result = await handle_utility_tool("get_vault_info", {}, mock_client)

        mock_client.get_vault_info.assert_awaited_once()
        assert "authenticated" in result


class TestUnknownTool:
    @pytest.mark.anyio
    async def test_raises_value_error(self, mock_client):
        with pytest.raises(ValueError, match="Unknown utility tool"):
            await handle_utility_tool("nonexistent", {}, mock_client)
