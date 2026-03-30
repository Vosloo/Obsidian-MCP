"""Tests for search tools."""

import pytest

from obsidian_mcp.tools.search import _search_in_content, handle_search_tool

# ---------------------------------------------------------------------------
# _search_in_content
# ---------------------------------------------------------------------------


class TestSearchInContent:
    @pytest.mark.anyio
    async def test_case_insensitive_match(self):
        content = "Line one\nHello World\nLine three"
        matches = await _search_in_content(content, "hello")
        assert len(matches) == 1
        assert matches[0]["line"] == 2
        assert "Hello World" in matches[0]["content"]

    @pytest.mark.anyio
    async def test_case_sensitive_no_match(self):
        content = "Hello World"
        matches = await _search_in_content(content, "hello", case_sensitive=True)
        assert len(matches) == 0

    @pytest.mark.anyio
    async def test_case_sensitive_match(self):
        content = "Hello World"
        matches = await _search_in_content(content, "Hello", case_sensitive=True)
        assert len(matches) == 1

    @pytest.mark.anyio
    async def test_multiple_matches(self):
        content = "apple\nbanana\napple pie\norange"
        matches = await _search_in_content(content, "apple")
        assert len(matches) == 2
        assert matches[0]["line"] == 1
        assert matches[1]["line"] == 3

    @pytest.mark.anyio
    async def test_no_matches(self):
        content = "nothing here"
        matches = await _search_in_content(content, "missing")
        assert len(matches) == 0

    @pytest.mark.anyio
    async def test_context_extraction(self):
        content = "x" * 100 + "TARGET" + "y" * 100
        matches = await _search_in_content(content, "TARGET")
        assert len(matches) == 1
        ctx = matches[0]["context"]
        assert "TARGET" in ctx
        # Context should be trimmed, not the full 206-char line
        assert len(ctx) < 200


# ---------------------------------------------------------------------------
# handle_search_tool
# ---------------------------------------------------------------------------


class TestListVaultFiles:
    @pytest.mark.anyio
    async def test_returns_listing(self, mock_client):
        mock_client.list_vault_root.return_value = {"files": ["a.md", "b.md"]}

        result = await handle_search_tool("list_vault_files", {}, mock_client)

        mock_client.list_vault_root.assert_awaited_once()
        assert "a.md" in result


class TestListDirectory:
    @pytest.mark.anyio
    async def test_returns_listing(self, mock_client):
        mock_client.list_directory.return_value = {"files": ["note.md"]}

        result = await handle_search_tool("list_directory", {"path": "NPCs"}, mock_client)

        mock_client.list_directory.assert_awaited_once_with(path="NPCs")
        assert "note.md" in result


class TestSearchByFilename:
    @pytest.mark.anyio
    async def test_wildcard_match_in_directory(self, mock_client):
        mock_client.list_directory.return_value = {
            "files": ["dragon.md", "dragonborn.md", "elf.md"]
        }

        result = await handle_search_tool(
            "search_by_filename", {"pattern": "dragon*", "directory": "Bestiary"}, mock_client
        )

        assert "dragon.md" in result
        assert "dragonborn.md" in result
        assert "elf.md" not in result

    @pytest.mark.anyio
    async def test_no_matches_in_directory(self, mock_client):
        mock_client.list_directory.return_value = {"files": ["elf.md"]}

        result = await handle_search_tool(
            "search_by_filename", {"pattern": "dragon*", "directory": "Bestiary"}, mock_client
        )

        assert "No files found" in result

    @pytest.mark.anyio
    async def test_searches_specific_directory(self, mock_client):
        mock_client.list_directory.return_value = {"files": ["session1.md", "session2.md"]}

        result = await handle_search_tool(
            "search_by_filename", {"pattern": "session*", "directory": "Sessions"}, mock_client
        )

        mock_client.list_directory.assert_awaited_once_with("Sessions")
        assert "session1.md" in result

    @pytest.mark.anyio
    async def test_vault_wide_search(self, mock_client):
        mock_client.search_jsonlogic.return_value = [
            {"filename": "0-Campaign/NPCs/Gandor.md", "result": True},
            {"filename": "0-Campaign/NPCs/Sella.md", "result": True},
            {"filename": "README.md", "result": True},
        ]

        result = await handle_search_tool(
            "search_by_filename", {"pattern": "*.md"}, mock_client
        )

        # Should use JsonLogic tautology to fetch all notes, not list_vault_root
        mock_client.list_vault_root.assert_not_awaited()
        mock_client.search_jsonlogic.assert_awaited_once_with({"==": [1, 1]})
        assert "Gandor.md" in result
        assert "Sella.md" in result
        assert "entire vault" in result

    @pytest.mark.anyio
    async def test_vault_wide_search_matches_filename_only(self, mock_client):
        """Pattern should match against the filename portion, not the full path."""
        mock_client.search_jsonlogic.return_value = [
            {"filename": "0-Campaign/NPCs/Gandor.md", "result": True},
            {"filename": "0-Campaign/Sessions/session1.md", "result": True},
        ]

        result = await handle_search_tool(
            "search_by_filename", {"pattern": "Gandor*"}, mock_client
        )

        assert "Gandor.md" in result
        assert "session1.md" not in result

    @pytest.mark.anyio
    async def test_vault_wide_no_matches(self, mock_client):
        mock_client.search_jsonlogic.return_value = []

        result = await handle_search_tool(
            "search_by_filename", {"pattern": "dragon*"}, mock_client
        )

        assert "No files found" in result

    @pytest.mark.anyio
    async def test_vault_wide_search_error(self, mock_client):
        mock_client.search_jsonlogic.side_effect = Exception("API unavailable")

        result = await handle_search_tool(
            "search_by_filename", {"pattern": "dragon*"}, mock_client
        )

        assert "Vault-wide search failed" in result


class TestSearchInNote:
    @pytest.mark.anyio
    async def test_finds_matches(self, mock_client):
        mock_client.get_note.return_value = "Line one\ndragon appears\nLine three"

        result = await handle_search_tool(
            "search_in_note", {"path": "note.md", "query": "dragon"}, mock_client
        )

        assert "dragon" in result
        assert "total_matches" in result

    @pytest.mark.anyio
    async def test_no_matches(self, mock_client):
        mock_client.get_note.return_value = "nothing relevant here"

        result = await handle_search_tool(
            "search_in_note", {"path": "note.md", "query": "dragon"}, mock_client
        )

        assert "No matches found" in result

    @pytest.mark.anyio
    async def test_title_only_match(self, mock_client):
        """Filename matches query but content does not — should still return a result."""
        mock_client.get_note.return_value = "no relevant content here"

        result = await handle_search_tool(
            "search_in_note", {"path": "NPCs/earth-foo.md", "query": "earth"}, mock_client
        )

        assert "total_matches" in result
        assert "'line': 0" in result
        assert "note title" in result

    @pytest.mark.anyio
    async def test_title_and_content_match_counts(self, mock_client):
        """Title match + one content match → total_matches == 2."""
        mock_client.get_note.return_value = "earth appears in body"

        result = await handle_search_tool(
            "search_in_note", {"path": "earth-foo.md", "query": "earth"}, mock_client
        )

        assert "'total_matches': 2" in result

    @pytest.mark.anyio
    async def test_no_spurious_title_match(self, mock_client):
        """Query not in filename — no line-0 title match should appear."""
        mock_client.get_note.return_value = "earth is mentioned here"

        result = await handle_search_tool(
            "search_in_note", {"path": "unrelated-note.md", "query": "earth"}, mock_client
        )

        assert "'line': 0" not in result

    @pytest.mark.anyio
    async def test_title_match_case_insensitive_default(self, mock_client):
        """Title matching is case-insensitive by default."""
        mock_client.get_note.return_value = "no relevant content"

        result = await handle_search_tool(
            "search_in_note", {"path": "Earth-Foo.md", "query": "earth"}, mock_client
        )

        assert "total_matches" in result
        assert "'line': 0" in result

    @pytest.mark.anyio
    async def test_title_match_case_sensitive_no_match(self, mock_client):
        """With case_sensitive=True, 'earth' must not match 'Earth-Foo'."""
        mock_client.get_note.return_value = "no relevant content"

        result = await handle_search_tool(
            "search_in_note",
            {"path": "Earth-Foo.md", "query": "earth", "case_sensitive": True},
            mock_client,
        )

        assert "No matches found" in result


class TestSearchInDirectory:
    @pytest.mark.anyio
    async def test_searches_md_files(self, mock_client):
        mock_client.list_directory.return_value = {"files": ["a.md", "b.md", "image.png"]}
        mock_client.get_note.side_effect = [
            "contains dragon here",  # a.md
            "no match",  # b.md
        ]

        result = await handle_search_tool(
            "search_in_directory", {"directory": "NPCs", "query": "dragon"}, mock_client
        )

        assert "dragon" in result
        assert "files_with_matches" in result

    @pytest.mark.anyio
    async def test_no_matches(self, mock_client):
        mock_client.list_directory.return_value = {"files": ["a.md"]}
        mock_client.get_note.return_value = "nothing here"

        result = await handle_search_tool(
            "search_in_directory", {"directory": "NPCs", "query": "dragon"}, mock_client
        )

        assert "No matches found" in result

    @pytest.mark.anyio
    async def test_handles_read_errors_gracefully(self, mock_client):
        mock_client.list_directory.return_value = {"files": ["a.md", "b.md"]}
        mock_client.get_note.side_effect = [
            Exception("read error"),
            "found dragon here",
        ]

        result = await handle_search_tool(
            "search_in_directory", {"directory": "NPCs", "query": "dragon"}, mock_client
        )

        # Should still find the match in b.md despite a.md failing
        assert "dragon" in result

    @pytest.mark.anyio
    async def test_title_only_match_surfaces_file(self, mock_client):
        """A file whose content has no match but whose filename does must appear in results."""
        mock_client.list_directory.return_value = {"files": ["earth-foo.md", "mars.md"]}
        mock_client.get_note.side_effect = [
            "no relevant content",  # earth-foo.md
            "no relevant content",  # mars.md
        ]

        result = await handle_search_tool(
            "search_in_directory", {"directory": "NPCs", "query": "earth"}, mock_client
        )

        assert "earth-foo.md" in result
        assert "mars.md" not in result

    @pytest.mark.anyio
    async def test_title_match_preview_has_line_zero(self, mock_client):
        """When a title-only match is the preview, line should be 0 and context should say 'note title'."""
        mock_client.list_directory.return_value = {"files": ["earth-foo.md"]}
        mock_client.get_note.return_value = "no relevant content"

        result = await handle_search_tool(
            "search_in_directory", {"directory": "Notes", "query": "earth"}, mock_client
        )

        assert "'line': 0" in result
        assert "note title" in result

    @pytest.mark.anyio
    async def test_max_results_limits_files_not_match_count(self, mock_client):
        """max_results should cap result *files*, not accumulated match count.

        Regression: previously the loop broke when total line-matches >= max_results,
        so a file with many matches would cause later files to be skipped entirely.
        """
        # a.md has 25 matches (exceeds default max_results=20 on its own)
        # b.md also matches and must still appear in results
        mock_client.list_directory.return_value = {"files": ["a.md", "b.md"]}
        mock_client.get_note.side_effect = [
            "\n".join(["dragon"] * 25),  # a.md: 25 matches
            "dragon appears once",        # b.md: 1 match
        ]

        result = await handle_search_tool(
            "search_in_directory", {"directory": "NPCs", "query": "dragon"}, mock_client
        )

        # Both files must appear — the high match count in a.md must not stop b.md from being searched
        assert "'NPCs/a.md'" in result
        assert "'NPCs/b.md'" in result


class TestUnknownTool:
    @pytest.mark.anyio
    async def test_raises_value_error(self, mock_client):
        with pytest.raises(ValueError, match="Unknown search tool"):
            await handle_search_tool("nonexistent", {}, mock_client)
