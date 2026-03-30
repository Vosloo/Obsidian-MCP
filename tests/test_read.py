"""Tests for read tools."""

import pytest

from obsidian_mcp.tools.read import handle_read_tool


class TestReadNote:
    @pytest.mark.anyio
    async def test_returns_json(self, mock_client):
        mock_client.get_note.return_value = {"content": "hello", "frontmatter": {}}

        result = await handle_read_tool("read_note", {"path": "Notes/a.md"}, mock_client)

        mock_client.get_note.assert_awaited_once_with(path="Notes/a.md", as_json=True)
        assert "hello" in result


class TestReadNoteMarkdown:
    @pytest.mark.anyio
    async def test_returns_raw_markdown(self, mock_client):
        mock_client.get_note.return_value = "# Title\n\nBody text."

        result = await handle_read_tool("read_note_markdown", {"path": "Notes/a.md"}, mock_client)

        mock_client.get_note.assert_awaited_once_with(path="Notes/a.md", as_json=False)
        assert "Title" in result


class TestGetDailyNote:
    @pytest.mark.anyio
    async def test_with_date(self, mock_client):
        mock_client.get_periodic_note.return_value = {"content": "daily"}

        result = await handle_read_tool(
            "get_daily_note", {"year": 2026, "month": 2, "day": 6}, mock_client
        )

        mock_client.get_periodic_note.assert_awaited_once_with(
            period="daily", year=2026, month=2, day=6, as_json=True
        )
        assert "daily" in result

    @pytest.mark.anyio
    async def test_without_date(self, mock_client):
        mock_client.get_periodic_note.return_value = {"content": "today"}

        result = await handle_read_tool("get_daily_note", {}, mock_client)

        mock_client.get_periodic_note.assert_awaited_once_with(
            period="daily", year=None, month=None, day=None, as_json=True
        )
        assert "today" in result


class TestUnknownTool:
    @pytest.mark.anyio
    async def test_raises_value_error(self, mock_client):
        with pytest.raises(ValueError, match="Unknown read tool"):
            await handle_read_tool("nonexistent", {}, mock_client)
