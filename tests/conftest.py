"""Shared test fixtures."""

from unittest.mock import AsyncMock

import pytest

from obsidian_mcp.client import ObsidianClient


@pytest.fixture
def mock_client() -> AsyncMock:
    """Return an AsyncMock spec'd to ObsidianClient.

    Individual tests should configure return values as needed, e.g.:
        mock_client.get_note.return_value = {"content": "..."}
    """
    return AsyncMock(spec=ObsidianClient)
