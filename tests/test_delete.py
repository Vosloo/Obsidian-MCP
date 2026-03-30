"""Tests for delete tools."""

import pytest

from obsidian_mcp.tools.delete import handle_delete_tool


class TestDeleteNote:
    @pytest.mark.anyio
    async def test_deletes_note(self, mock_client):
        result = await handle_delete_tool("delete_note", {"path": "old.md"}, mock_client)

        mock_client.delete_note.assert_awaited_once_with(path="old.md")
        assert "old.md" in result


class TestUnknownTool:
    @pytest.mark.anyio
    async def test_raises_value_error(self, mock_client):
        with pytest.raises(ValueError, match="Unknown delete tool"):
            await handle_delete_tool("nonexistent", {}, mock_client)
