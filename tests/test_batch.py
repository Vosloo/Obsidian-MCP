"""Tests for batch tools."""

import pytest

from obsidian_mcp.tools.batch import handle_batch_tool


class TestBatchReadNotes:
    @pytest.mark.anyio
    async def test_reads_multiple_notes(self, mock_client):
        mock_client.get_note.side_effect = [
            {"content": "note1"},
            {"content": "note2"},
        ]

        result = await handle_batch_tool(
            "batch_read_notes", {"paths": ["a.md", "b.md"]}, mock_client
        )

        assert mock_client.get_note.await_count == 2
        assert "note1" in result
        assert "note2" in result


class TestBatchAppendToNotes:
    @pytest.mark.anyio
    async def test_appends_to_multiple_notes(self, mock_client):
        ops = [
            {"path": "a.md", "content": "extra1"},
            {"path": "b.md", "content": "extra2"},
        ]

        result = await handle_batch_tool("batch_append_to_notes", {"operations": ops}, mock_client)

        assert mock_client.append_to_note.await_count == 2
        assert "2 notes" in result


class TestBatchDeleteNotes:
    @pytest.mark.anyio
    async def test_deletes_multiple_notes(self, mock_client):
        result = await handle_batch_tool(
            "batch_delete_notes", {"paths": ["a.md", "b.md", "c.md"]}, mock_client
        )

        assert mock_client.delete_note.await_count == 3
        assert "3 notes" in result


class TestUnknownTool:
    @pytest.mark.anyio
    async def test_raises_value_error(self, mock_client):
        with pytest.raises(ValueError, match="Unknown batch tool"):
            await handle_batch_tool("nonexistent", {}, mock_client)
