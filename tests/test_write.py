"""Tests for write tools."""

import pytest

from obsidian_mcp.tools.write import _find_section, handle_write_tool

# ---------------------------------------------------------------------------
# _find_section
# ---------------------------------------------------------------------------

SAMPLE_NOTE = [
    "# Title",
    "",
    "Some intro text.",
    "",
    "## Section A",
    "",
    "Content of A.",
    "",
    "## Section B",
    "",
    "Content of B.",
    "",
    "### Subsection B1",
    "",
    "Nested content.",
    "",
    "## Section C",
    "",
    "Content of C.",
]


class TestFindSection:
    def test_finds_first_section(self):
        result = _find_section(SAMPLE_NOTE, "Section A")
        assert result is not None
        start, end = result
        assert SAMPLE_NOTE[start].strip().endswith("Section A")
        # Should end just before "## Section B"
        assert end == 7

    def test_finds_middle_section(self):
        result = _find_section(SAMPLE_NOTE, "Section B")
        assert result is not None
        start, end = result
        assert SAMPLE_NOTE[start].strip().endswith("Section B")
        # Section B includes its subsection B1, ends before Section C
        assert end == 15

    def test_finds_last_section(self):
        result = _find_section(SAMPLE_NOTE, "Section C")
        assert result is not None
        start, end = result
        assert end == len(SAMPLE_NOTE) - 1

    def test_finds_nested_subsection(self):
        result = _find_section(SAMPLE_NOTE, "Subsection B1")
        assert result is not None
        start, end = result
        assert SAMPLE_NOTE[start].strip().endswith("Subsection B1")
        # Subsection B1 ends before Section C (higher-level heading)
        assert end == 15

    def test_heading_not_found(self):
        result = _find_section(SAMPLE_NOTE, "Nonexistent")
        assert result is None

    def test_finds_top_level_heading(self):
        result = _find_section(SAMPLE_NOTE, "Title")
        assert result is not None
        start, end = result
        assert start == 0
        # Title section ends before the first ## heading
        assert end == 3

    def test_empty_document(self):
        result = _find_section([], "Anything")
        assert result is None

    def test_single_heading_only(self):
        lines = ["## Only Heading", "", "Some content."]
        result = _find_section(lines, "Only Heading")
        assert result == (0, 2)


# ---------------------------------------------------------------------------
# handle_write_tool
# ---------------------------------------------------------------------------


class TestCreateNote:
    @pytest.mark.anyio
    async def test_creates_note(self, mock_client):
        result = await handle_write_tool(
            "create_note", {"path": "Notes/test.md", "content": "# Hello"}, mock_client
        )
        mock_client.create_note.assert_awaited_once_with(path="Notes/test.md", content="# Hello")
        assert "Notes/test.md" in result


class TestAppendToNote:
    @pytest.mark.anyio
    async def test_appends_content(self, mock_client):
        result = await handle_write_tool(
            "append_to_note", {"path": "Notes/test.md", "content": "extra"}, mock_client
        )
        mock_client.append_to_note.assert_awaited_once_with(path="Notes/test.md", content="extra")
        assert "Notes/test.md" in result


class TestUpdateSection:
    @pytest.mark.anyio
    async def test_replaces_section(self, mock_client):
        note_content = "# Title\n\nIntro.\n\n## Target\n\nOld content.\n\n## Other\n\nKeep this."
        mock_client.get_note.return_value = note_content

        result = await handle_write_tool(
            "update_section",
            {"path": "note.md", "heading": "Target", "content": "New content."},
            mock_client,
        )

        mock_client.create_note.assert_awaited_once()
        written_content = mock_client.create_note.call_args[0][1]
        assert "New content." in written_content
        assert "Old content." not in written_content
        assert "Keep this." in written_content
        assert "Target" in result

    @pytest.mark.anyio
    async def test_heading_not_found_returns_error(self, mock_client):
        mock_client.get_note.return_value = "# Title\n\n## Existing\n\nContent."

        result = await handle_write_tool(
            "update_section",
            {"path": "note.md", "heading": "Missing", "content": "x"},
            mock_client,
        )

        assert "Error" in result
        assert "Missing" in result
        assert "Existing" in result  # lists available headings


class TestUpdateFrontmatter:
    @pytest.mark.anyio
    async def test_delegates_to_client(self, mock_client):
        result = await handle_write_tool(
            "update_frontmatter",
            {"path": "note.md", "key": "status", "value": "done", "operation": "replace"},
            mock_client,
        )
        mock_client.update_frontmatter.assert_awaited_once_with(
            path="note.md", key="status", value="done", operation="replace"
        )
        assert "status" in result

    @pytest.mark.anyio
    async def test_default_operation_is_replace(self, mock_client):
        await handle_write_tool(
            "update_frontmatter",
            {"path": "note.md", "key": "tag", "value": "new"},
            mock_client,
        )
        mock_client.update_frontmatter.assert_awaited_once_with(
            path="note.md", key="tag", value="new", operation="replace"
        )


class TestMoveNote:
    @pytest.mark.anyio
    async def test_moves_note_successfully(self, mock_client):
        mock_client.get_note.return_value = "# Gandor\n\nContent."

        result = await handle_write_tool(
            "move_note",
            {"source_path": "NPCs/Gandor.md", "destination_dir": "Archive"},
            mock_client,
        )

        mock_client.get_note.assert_awaited_once_with("NPCs/Gandor.md", as_json=False)
        mock_client.create_note.assert_awaited_once_with("Archive/Gandor.md", "# Gandor\n\nContent.")
        mock_client.delete_note.assert_awaited_once_with("NPCs/Gandor.md")
        assert "NPCs/Gandor.md" in result
        assert "Archive/Gandor.md" in result

    @pytest.mark.anyio
    async def test_preserves_filename_from_nested_source(self, mock_client):
        mock_client.get_note.return_value = "content"

        result = await handle_write_tool(
            "move_note",
            {"source_path": "0-Campaign/2-Locations/Q'Barra/Places/Newthrone.md", "destination_dir": "Archive"},
            mock_client,
        )

        mock_client.create_note.assert_awaited_once_with("Archive/Newthrone.md", "content")
        assert "Newthrone.md" in result

    @pytest.mark.anyio
    async def test_strips_trailing_slash_from_destination(self, mock_client):
        mock_client.get_note.return_value = "content"

        await handle_write_tool(
            "move_note",
            {"source_path": "NPCs/Gandor.md", "destination_dir": "Archive/"},
            mock_client,
        )

        mock_client.create_note.assert_awaited_once_with("Archive/Gandor.md", "content")

    @pytest.mark.anyio
    async def test_source_read_error_aborts(self, mock_client):
        mock_client.get_note.side_effect = Exception("Not found")

        result = await handle_write_tool(
            "move_note",
            {"source_path": "NPCs/Missing.md", "destination_dir": "Archive"},
            mock_client,
        )

        assert "Error reading source note" in result
        mock_client.create_note.assert_not_awaited()
        mock_client.delete_note.assert_not_awaited()

    @pytest.mark.anyio
    async def test_destination_create_error_aborts(self, mock_client):
        mock_client.get_note.return_value = "content"
        mock_client.create_note.side_effect = Exception("Permission denied")

        result = await handle_write_tool(
            "move_note",
            {"source_path": "NPCs/Gandor.md", "destination_dir": "Archive"},
            mock_client,
        )

        assert "Error creating note" in result
        mock_client.delete_note.assert_not_awaited()

    @pytest.mark.anyio
    async def test_delete_failure_returns_warning(self, mock_client):
        mock_client.get_note.return_value = "content"
        mock_client.delete_note.side_effect = Exception("Locked")

        result = await handle_write_tool(
            "move_note",
            {"source_path": "NPCs/Gandor.md", "destination_dir": "Archive"},
            mock_client,
        )

        assert "Warning" in result
        assert "Archive/Gandor.md" in result
        assert "NPCs/Gandor.md" in result


class TestUnknownTool:
    @pytest.mark.anyio
    async def test_raises_value_error(self, mock_client):
        with pytest.raises(ValueError, match="Unknown write tool"):
            await handle_write_tool("nonexistent", {}, mock_client)
