"""Tests for ObsidianClient construction."""

from unittest.mock import patch

import pytest

from obsidian_mcp.client import ObsidianClient


class TestClientInit:
    def test_missing_api_key_raises(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="OBSIDIAN_API_KEY"),
        ):
            ObsidianClient(api_url="http://localhost:27123", api_key="")

    def test_custom_url_and_key(self):
        client = ObsidianClient(api_url="http://myhost:9999", api_key="secret")
        assert client.api_url == "http://myhost:9999"
        assert client.api_key == "secret"

    def test_trailing_slash_stripped(self):
        client = ObsidianClient(api_url="http://localhost:27123/", api_key="key")
        assert client.api_url == "http://localhost:27123"

    def test_defaults_from_env(self):
        env = {
            "OBSIDIAN_API_URL": "http://env-host:1234",
            "OBSIDIAN_API_KEY": "env-key",
        }
        with patch.dict("os.environ", env, clear=True):
            client = ObsidianClient()
            assert client.api_url == "http://env-host:1234"
            assert client.api_key == "env-key"

    def test_default_url_when_env_missing(self):
        env = {"OBSIDIAN_API_KEY": "key"}
        with patch.dict("os.environ", env, clear=True):
            client = ObsidianClient()
            assert client.api_url == "http://127.0.0.1:27123"
