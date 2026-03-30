"""Tests for tree tools."""

import pytest

from obsidian_mcp.tools.tree import handle_tree_tool


class TestTreeView:
    @pytest.mark.anyio
    async def test_basic_tree(self, mock_client):
        mock_client.list_vault_root.return_value = {"files": ["notes/", "readme.md"]}
        mock_client.list_directory.return_value = {"files": ["a.md", "b.md"]}

        result = await handle_tree_tool("tree_view", {"path": "", "max_depth": 2}, mock_client)

        assert "/" in result  # root
        assert "notes/" in result
        assert "readme.md" in result
        assert "a.md" in result

    @pytest.mark.anyio
    async def test_depth_limiting(self, mock_client):
        mock_client.list_vault_root.return_value = {"files": ["deep/", "top.md"]}
        # With max_depth=1 the subdirectory should not be recursed into
        mock_client.list_directory.return_value = {"files": ["nested.md"]}

        result = await handle_tree_tool("tree_view", {"path": "", "max_depth": 1}, mock_client)

        assert "deep/" in result
        assert "top.md" in result
        # nested.md should NOT appear because depth is limited to 1
        assert "nested.md" not in result

    @pytest.mark.anyio
    async def test_empty_directory(self, mock_client):
        mock_client.list_vault_root.return_value = {"files": []}

        result = await handle_tree_tool("tree_view", {}, mock_client)

        # Should just have the root marker
        assert "/" in result

    @pytest.mark.anyio
    async def test_tree_connectors(self, mock_client):
        mock_client.list_vault_root.return_value = {"files": ["a.md", "b.md"]}

        result = await handle_tree_tool("tree_view", {"path": "", "max_depth": 1}, mock_client)

        assert "\u251c\u2500\u2500 " in result  # ├──
        assert "\u2514\u2500\u2500 " in result  # └──


    @pytest.mark.anyio
    async def test_exclude_dirs_parameter(self, mock_client):
        mock_client.list_vault_root.return_value = {
            "files": ["notes/", "mechanics/", "readme.md"]
        }
        mock_client.list_directory.return_value = {"files": ["a.md"]}

        result = await handle_tree_tool(
            "tree_view",
            {"path": "", "max_depth": 2, "exclude_dirs": ["mechanics"]},
            mock_client,
        )

        assert "mechanics/  [excluded]" in result
        assert "a.md" in result
        mock_client.list_directory.assert_awaited_once_with("notes")

    @pytest.mark.anyio
    async def test_exclude_dirs_env_var(self, mock_client, monkeypatch):
        monkeypatch.setenv("TREE_VIEW_EXCLUDE_DIRS", "mechanics")
        mock_client.list_vault_root.return_value = {
            "files": ["notes/", "mechanics/"]
        }
        mock_client.list_directory.return_value = {"files": []}

        result = await handle_tree_tool("tree_view", {}, mock_client)

        assert "mechanics/  [excluded]" in result
        mock_client.list_directory.assert_awaited_once_with("notes")

    @pytest.mark.anyio
    async def test_exclude_dirs_merged(self, mock_client, monkeypatch):
        monkeypatch.setenv("TREE_VIEW_EXCLUDE_DIRS", "mechanics")
        mock_client.list_vault_root.return_value = {
            "files": ["notes/", "mechanics/", "archive/"]
        }
        mock_client.list_directory.return_value = {"files": []}

        result = await handle_tree_tool(
            "tree_view",
            {"exclude_dirs": ["archive"]},
            mock_client,
        )

        assert "mechanics/  [excluded]" in result
        assert "archive/  [excluded]" in result
        mock_client.list_directory.assert_awaited_once_with("notes")

    @pytest.mark.anyio
    async def test_exclude_dirs_not_applied_to_root(self, mock_client):
        mock_client.list_directory.return_value = {"files": ["spell.md", "monster.md"]}

        result = await handle_tree_tool(
            "tree_view",
            {"path": "mechanics", "max_depth": 1, "exclude_dirs": ["mechanics"]},
            mock_client,
        )

        assert "spell.md" in result
        assert "monster.md" in result
        assert "[excluded]" not in result


class TestUnknownTool:
    @pytest.mark.anyio
    async def test_raises_value_error(self, mock_client):
        with pytest.raises(ValueError, match="Unknown tree tool"):
            await handle_tree_tool("nonexistent", {}, mock_client)
