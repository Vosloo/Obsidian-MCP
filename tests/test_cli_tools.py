"""Tests for CLI-backed tools (get_tags, get_unresolved_links) and move_note CLI path."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from obsidian_mcp.cli import CLIResult, ObsidianCLI
from obsidian_mcp.tools.cli_tools import _extract_json, _in_dir, _parse_sources, handle_cli_tool
from obsidian_mcp.tools.write import handle_write_tool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cli(available: bool = True, returncode: int = 0, stdout: str = "", stderr: str = "") -> ObsidianCLI:
    """Return a mock ObsidianCLI."""
    cli = MagicMock(spec=ObsidianCLI)
    cli.available = available
    cli.run = AsyncMock(return_value=CLIResult(returncode=returncode, stdout=stdout, stderr=stderr))
    return cli


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------

class TestExtractJson:
    def test_clean_json_array(self):
        assert _extract_json('[{"a": 1}]') == '[{"a": 1}]'

    def test_strips_leading_log_lines(self):
        text = "2026-03-30 Loading package...\nYour installer is out of date.\n[1, 2, 3]"
        assert _extract_json(text) == "[1, 2, 3]"

    def test_finds_object_when_no_array(self):
        text = "log line\n{\"key\": \"val\"}"
        assert _extract_json(text) == '{"key": "val"}'

    def test_returns_none_when_no_json(self):
        assert _extract_json("just plain text") is None

    def test_empty_string(self):
        assert _extract_json("") is None


# ---------------------------------------------------------------------------
# _parse_sources
# ---------------------------------------------------------------------------

class TestParseSources:
    def test_single_string_path(self):
        assert _parse_sources("note.md") == ["note.md"]

    def test_comma_separated_string(self):
        # Real CLI format for multiple sources
        assert _parse_sources("_mcp_test/note-a.md, _mcp_test/note-b.md") == [
            "_mcp_test/note-a.md",
            "_mcp_test/note-b.md",
        ]

    def test_list_passthrough(self):
        assert _parse_sources(["a.md", "b.md"]) == ["a.md", "b.md"]

    def test_none_returns_empty(self):
        assert _parse_sources(None) == []

    def test_strips_whitespace(self):
        assert _parse_sources(" a.md , b.md ") == ["a.md", "b.md"]


# ---------------------------------------------------------------------------
# _in_dir
# ---------------------------------------------------------------------------

class TestInDir:
    def test_direct_child(self):
        assert _in_dir("Sessions/note.md", "Sessions") is True

    def test_nested_child(self):
        assert _in_dir("Sessions/2024/note.md", "Sessions") is True

    def test_not_in_dir(self):
        assert _in_dir("NPCs/Gandor.md", "Sessions") is False

    def test_prefix_without_slash_does_not_match(self):
        # "Session" should not match "Sessions/note.md"
        assert _in_dir("Sessions/note.md", "Session") is False

    def test_trailing_slash_on_directory_arg(self):
        assert _in_dir("Sessions/note.md", "Sessions/") is True

    def test_backslash_separator(self):
        assert _in_dir("Sessions\\note.md", "Sessions") is True


# ---------------------------------------------------------------------------
# CLIResult
# ---------------------------------------------------------------------------

class TestCLIResult:
    def test_ok_when_zero_and_clean_output(self):
        assert CLIResult(returncode=0, stdout="Moved: a -> b", stderr="").ok is True

    def test_not_ok_when_nonzero(self):
        assert CLIResult(returncode=1, stdout="", stderr="err").ok is False

    def test_not_ok_when_stdout_contains_error_line(self):
        # CLI always exits 0; errors appear as "Error: ..." in stdout
        stdout = (
            "2026-03-30 Loading...\n"
            "Your Obsidian installer is out of date.\n"
            'Error: Command "bad_cmd" not found.'
        )
        assert CLIResult(returncode=0, stdout=stdout, stderr="").ok is False

    def test_not_ok_when_enoent_in_stdout(self):
        stdout = "Error: ENOENT: no such file or directory, rename 'a' -> 'b'"
        assert CLIResult(returncode=0, stdout=stdout, stderr="").ok is False

    def test_ok_with_log_prefix_and_json(self):
        stdout = "2026-03-30 Loading...\nYour Obsidian installer is out of date.\n[{}]"
        assert CLIResult(returncode=0, stdout=stdout, stderr="").ok is True


# ---------------------------------------------------------------------------
# get_tags
# ---------------------------------------------------------------------------

class TestGetTags:
    @pytest.mark.anyio
    async def test_returns_not_available_when_cli_missing(self):
        cli = make_cli(available=False)
        result = await handle_cli_tool("get_tags", {}, cli)
        assert "not available" in result.lower()
        cli.run.assert_not_awaited()

    @pytest.mark.anyio
    async def test_parses_json_output(self):
        data = [{"tag": "#project", "count": 5}, {"tag": "#idea", "count": 2}]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool("get_tags", {}, cli)
        assert "#project: 5" in result
        assert "#idea: 2" in result

    @pytest.mark.anyio
    async def test_handles_string_count(self):
        # Real CLI returns count as a string
        data = [{"tag": "#ttrpg", "count": "17124"}]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool("get_tags", {}, cli)
        assert "#ttrpg: 17124" in result

    @pytest.mark.anyio
    async def test_strips_cli_log_prefix(self):
        # Real CLI prepends log lines to stdout before the JSON
        prefix = "2026-03-30 Loading package...\nYour installer is out of date.\n"
        data = [{"tag": "#idea", "count": "3"}]
        cli = make_cli(stdout=prefix + json.dumps(data))
        result = await handle_cli_tool("get_tags", {}, cli)
        assert "#idea: 3" in result

    @pytest.mark.anyio
    async def test_empty_json_array(self):
        cli = make_cli(stdout="[]")
        result = await handle_cli_tool("get_tags", {}, cli)
        assert "no tags" in result.lower()

    @pytest.mark.anyio
    async def test_plain_text_fallback(self):
        cli = make_cli(stdout="#project\n#idea")
        result = await handle_cli_tool("get_tags", {}, cli)
        assert "#project" in result

    @pytest.mark.anyio
    async def test_cli_error_returns_message(self):
        # CLI exits 0 but prints "Error:" to stdout
        cli = make_cli(returncode=0, stdout="Error: Command not found.")
        result = await handle_cli_tool("get_tags", {}, cli)
        assert "Error" in result

    @pytest.mark.anyio
    async def test_runs_correct_args_no_path(self):
        cli = make_cli(stdout="[]")
        await handle_cli_tool("get_tags", {}, cli)
        cli.run.assert_awaited_once_with("tags", "counts", "sort=count", "format=json")

    @pytest.mark.anyio
    async def test_runs_with_path_arg(self):
        cli = make_cli(stdout="[]")
        await handle_cli_tool("get_tags", {"path": "Notes/foo.md"}, cli)
        cli.run.assert_awaited_once_with(
            "tags", "counts", "sort=count", "format=json", "path=Notes/foo.md"
        )


# ---------------------------------------------------------------------------
# get_unresolved_links
# ---------------------------------------------------------------------------

class TestGetUnresolvedLinks:
    @pytest.mark.anyio
    async def test_returns_not_available_when_cli_missing(self):
        cli = make_cli(available=False)
        result = await handle_cli_tool("get_unresolved_links", {}, cli)
        assert "not available" in result.lower()

    @pytest.mark.anyio
    async def test_parses_json_with_list_sources(self):
        data = [{"link": "Missing Note", "count": 3, "sources": ["file1.md", "file2.md"]}]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool("get_unresolved_links", {}, cli)
        assert "[[Missing Note]]" in result
        assert "3 references" in result
        assert "file1.md" in result

    @pytest.mark.anyio
    async def test_handles_string_count_and_string_sources(self):
        # Real CLI: count is string, sources is comma-separated string
        data = [{"link": "Missing Note", "count": "2", "sources": "file1.md, file2.md"}]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool("get_unresolved_links", {}, cli)
        assert "[[Missing Note]]" in result
        assert "2 references" in result
        assert "file1.md" in result
        assert "file2.md" in result

    @pytest.mark.anyio
    async def test_single_reference_grammar(self):
        data = [{"link": "Ghost", "count": "1", "sources": "file1.md"}]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool("get_unresolved_links", {}, cli)
        assert "1 reference)" in result  # not "1 references"

    @pytest.mark.anyio
    async def test_strips_cli_log_prefix(self):
        prefix = "2026-03-30 Loading package...\nYour installer is out of date.\n"
        data = [{"link": "Ghost Note", "count": "1", "sources": "a.md"}]
        cli = make_cli(stdout=prefix + json.dumps(data))
        result = await handle_cli_tool("get_unresolved_links", {}, cli)
        assert "[[Ghost Note]]" in result

    @pytest.mark.anyio
    async def test_exclude_dirs_hides_entries_from_excluded_dir(self):
        data = [
            {"link": "Excluded Ghost", "count": "1", "sources": "1-Mechanics/spell.md"},
            {"link": "Kept Ghost", "count": "1", "sources": "Notes/note.md"},
        ]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool(
            "get_unresolved_links", {"exclude_dirs": ["1-Mechanics"]}, cli
        )
        assert "[[Excluded Ghost]]" not in result
        assert "[[Kept Ghost]]" in result

    @pytest.mark.anyio
    async def test_exclude_dirs_keeps_entry_with_mixed_sources(self):
        # If one source is outside the excluded dir, the entry is kept
        data = [
            {
                "link": "Mixed Ghost",
                "count": "2",
                "sources": "1-Mechanics/spell.md, Notes/note.md",
            }
        ]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool(
            "get_unresolved_links", {"exclude_dirs": ["1-Mechanics"]}, cli
        )
        assert "[[Mixed Ghost]]" in result

    @pytest.mark.anyio
    async def test_directory_includes_only_matching_sources(self):
        data = [
            {"link": "In Scope", "count": "1", "sources": "Sessions/note.md"},
            {"link": "Out of Scope", "count": "1", "sources": "NPCs/gandor.md"},
        ]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool(
            "get_unresolved_links", {"directory": "Sessions"}, cli
        )
        assert "[[In Scope]]" in result
        assert "[[Out of Scope]]" not in result

    @pytest.mark.anyio
    async def test_directory_includes_entry_with_mixed_sources(self):
        # Entry where only ONE source is in the directory is still included
        data = [
            {
                "link": "Mixed",
                "count": "2",
                "sources": "Sessions/note.md, NPCs/gandor.md",
            }
        ]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool(
            "get_unresolved_links", {"directory": "Sessions"}, cli
        )
        assert "[[Mixed]]" in result

    @pytest.mark.anyio
    async def test_directory_trailing_slash_normalised(self):
        data = [{"link": "Ghost", "count": "1", "sources": "Sessions/note.md"}]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool(
            "get_unresolved_links", {"directory": "Sessions/"}, cli
        )
        assert "[[Ghost]]" in result

    @pytest.mark.anyio
    async def test_directory_and_exclude_dirs_together(self):
        # directory=Sessions, exclude_dirs=["Sessions/Archive"]
        # Entry whose only source is Sessions/Archive → excluded by exclude_dirs
        # Entry from Sessions/Current → kept
        data = [
            {"link": "Archived Ghost", "count": "1", "sources": "Sessions/Archive/old.md"},
            {"link": "Current Ghost", "count": "1", "sources": "Sessions/Current/new.md"},
            {"link": "Outside", "count": "1", "sources": "NPCs/gandor.md"},
        ]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool(
            "get_unresolved_links",
            {"directory": "Sessions", "exclude_dirs": ["Sessions/Archive"]},
            cli,
        )
        assert "[[Archived Ghost]]" not in result
        assert "[[Current Ghost]]" in result
        assert "[[Outside]]" not in result

    @pytest.mark.anyio
    async def test_exclude_dirs_from_env_var(self, monkeypatch):
        monkeypatch.setenv("TREE_VIEW_EXCLUDE_DIRS", "1-Mechanics")
        data = [
            {"link": "Env Excluded", "count": "1", "sources": "1-Mechanics/spell.md"},
            {"link": "Kept", "count": "1", "sources": "Notes/note.md"},
        ]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool("get_unresolved_links", {}, cli)
        assert "[[Env Excluded]]" not in result
        assert "[[Kept]]" in result

    @pytest.mark.anyio
    async def test_exclude_dirs_env_var_merged_with_arg(self, monkeypatch):
        monkeypatch.setenv("TREE_VIEW_EXCLUDE_DIRS", "1-Mechanics")
        data = [
            {"link": "Env Ghost", "count": "1", "sources": "1-Mechanics/spell.md"},
            {"link": "Arg Ghost", "count": "1", "sources": "Templates/template.md"},
            {"link": "Kept", "count": "1", "sources": "Notes/note.md"},
        ]
        cli = make_cli(stdout=json.dumps(data))
        result = await handle_cli_tool(
            "get_unresolved_links", {"exclude_dirs": ["Templates"]}, cli
        )
        assert "[[Env Ghost]]" not in result
        assert "[[Arg Ghost]]" not in result
        assert "[[Kept]]" in result

    @pytest.mark.anyio
    async def test_empty_json_array(self):
        cli = make_cli(stdout="[]")
        result = await handle_cli_tool("get_unresolved_links", {}, cli)
        assert "no unresolved" in result.lower()

    @pytest.mark.anyio
    async def test_cli_error_returns_message(self):
        cli = make_cli(returncode=0, stdout="Error: Command not found.")
        result = await handle_cli_tool("get_unresolved_links", {}, cli)
        assert "Error" in result

    @pytest.mark.anyio
    async def test_runs_correct_args(self):
        cli = make_cli(stdout="[]")
        await handle_cli_tool("get_unresolved_links", {}, cli)
        cli.run.assert_awaited_once_with("unresolved", "counts", "verbose", "format=json")


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------

class TestUnknownCliTool:
    @pytest.mark.anyio
    async def test_raises_value_error(self):
        cli = make_cli()
        with pytest.raises(ValueError, match="Unknown CLI tool"):
            await handle_cli_tool("nonexistent", {}, cli)


# ---------------------------------------------------------------------------
# move_note — CLI path
# ---------------------------------------------------------------------------

class TestMoveNoteCLI:
    @pytest.mark.anyio
    async def test_uses_cli_when_available(self, mock_client):
        cli = make_cli(returncode=0, stdout="")
        result = await handle_write_tool(
            "move_note",
            {"source_path": "NPCs/Gandor.md", "destination_dir": "Archive"},
            mock_client,
            cli,
        )
        # "move" must be first arg; to= takes the directory
        cli.run.assert_awaited_once_with(
            "move", "path=NPCs/Gandor.md", "to=Archive"
        )
        mock_client.get_note.assert_not_awaited()
        mock_client.create_note.assert_not_awaited()
        mock_client.delete_note.assert_not_awaited()
        assert "Archive/Gandor.md" in result

    @pytest.mark.anyio
    async def test_falls_back_to_rest_when_cli_unavailable(self, mock_client):
        cli = make_cli(available=False)
        mock_client.get_note.return_value = "# Gandor"

        result = await handle_write_tool(
            "move_note",
            {"source_path": "NPCs/Gandor.md", "destination_dir": "Archive"},
            mock_client,
            cli,
        )

        cli.run.assert_not_awaited()
        mock_client.get_note.assert_awaited_once()
        mock_client.create_note.assert_awaited_once()
        mock_client.delete_note.assert_awaited_once()
        assert "Archive/Gandor.md" in result

    @pytest.mark.anyio
    async def test_falls_back_to_rest_when_cli_fails(self, mock_client):
        # Real CLI: exits 0 but prints "Error:" to stdout
        cli = make_cli(returncode=0, stdout="Error: ENOENT: no such file or directory")
        mock_client.get_note.return_value = "# Gandor"

        await handle_write_tool(
            "move_note",
            {"source_path": "NPCs/Gandor.md", "destination_dir": "Archive"},
            mock_client,
            cli,
        )

        cli.run.assert_awaited_once()
        mock_client.get_note.assert_awaited_once()
        mock_client.create_note.assert_awaited_once()

    @pytest.mark.anyio
    async def test_no_cli_uses_rest(self, mock_client):
        mock_client.get_note.return_value = "content"

        result = await handle_write_tool(
            "move_note",
            {"source_path": "A/note.md", "destination_dir": "B"},
            mock_client,
            None,
        )

        mock_client.get_note.assert_awaited_once()
        mock_client.create_note.assert_awaited_once_with("B/note.md", "content")
        mock_client.delete_note.assert_awaited_once_with("A/note.md")
