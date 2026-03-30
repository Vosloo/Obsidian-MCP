"""Tests for directory tools."""

import pytest

from obsidian_mcp.tools.directory import handle_directory_tool


class TestCreateDirectory:
    @pytest.mark.anyio
    async def test_creates_placeholder_then_deletes(self, mock_client):
        result = await handle_directory_tool("create_directory", {"path": "NewDir"}, mock_client)

        mock_client.create_note.assert_awaited_once_with("NewDir/.placeholder", "")
        mock_client.delete_note.assert_awaited_once_with("NewDir/.placeholder")
        assert "NewDir" in result

    @pytest.mark.anyio
    async def test_handles_creation_error(self, mock_client):
        mock_client.create_note.side_effect = Exception("API error")

        result = await handle_directory_tool("create_directory", {"path": "Bad"}, mock_client)

        assert "Failed" in result


class TestDeleteDirectory:
    @pytest.mark.anyio
    async def test_deletes_files_recursively(self, mock_client):
        mock_client.list_directory.return_value = {"files": ["a.md", "b.md"]}

        result = await handle_directory_tool("delete_directory", {"path": "OldDir"}, mock_client)

        assert mock_client.delete_note.await_count == 2
        assert "Deleted 2 items" in result

    @pytest.mark.anyio
    async def test_recurses_into_subdirectories(self, mock_client):
        # First call lists parent dir, second call lists subdir
        mock_client.list_directory.side_effect = [
            {"files": ["sub/", "file.md"]},  # parent dir
            {"files": ["nested.md"]},  # sub dir
        ]

        result = await handle_directory_tool("delete_directory", {"path": "Parent"}, mock_client)

        # Should delete nested.md + sub/ (recursive) + file.md
        assert "Deleted" in result

    @pytest.mark.anyio
    async def test_empty_directory(self, mock_client):
        mock_client.list_directory.return_value = {"files": []}

        result = await handle_directory_tool("delete_directory", {"path": "Empty"}, mock_client)

        assert "empty" in result.lower() or "doesn't exist" in result.lower()

    @pytest.mark.anyio
    async def test_reports_errors(self, mock_client):
        mock_client.list_directory.return_value = {"files": ["a.md", "b.md"]}
        mock_client.delete_note.side_effect = [Exception("fail"), None]

        result = await handle_directory_tool("delete_directory", {"path": "Dir"}, mock_client)

        assert "Errors" in result or "Deleted 1 items" in result


class TestUnknownTool:
    @pytest.mark.anyio
    async def test_raises_value_error(self, mock_client):
        with pytest.raises(ValueError, match="Unknown directory tool"):
            await handle_directory_tool("nonexistent", {}, mock_client)
