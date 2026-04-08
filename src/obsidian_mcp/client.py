"""HTTP client for Obsidian Local REST API."""

import os
from typing import Any
from urllib.parse import quote

import httpx


class ObsidianClient:
    """Client for interacting with Obsidian Local REST API."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ):
        """Initialize the Obsidian client.

        Args:
            api_url: Base URL for the Obsidian API (default: from env OBSIDIAN_API_URL)
            api_key: API key for authentication (default: from env OBSIDIAN_API_KEY)
            timeout: Request timeout in seconds (default: 120s for large vault searches)
        """
        self.api_url = (api_url or os.getenv("OBSIDIAN_API_URL", "http://127.0.0.1:27123")).rstrip(
            "/"
        )
        self.api_key = api_key or os.getenv("OBSIDIAN_API_KEY", "")

        if not self.api_key:
            raise ValueError("OBSIDIAN_API_KEY must be set in environment or provided")

        # Disable SSL verification for self-signed certificates (local Obsidian API)
        # Use longer timeout for search operations on large vaults
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=httpx.Timeout(timeout, read=timeout * 2),  # Double timeout for read ops
            verify=False,  # Obsidian uses self-signed certificates
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # Search operations
    async def search_simple(self, query: str, context_length: int = 100) -> list[dict[str, Any]]:
        """Perform simple text search.

        Args:
            query: Search query string
            context_length: Number of characters of context around matches

        Returns:
            List of search results with file paths and matching content
        """
        try:
            response = await self.client.post(
                "/search/simple/",
                json={"query": query, "contextLength": context_length},
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise TimeoutError(
                "Search timed out. Your vault may be large. Try a more specific query."
            ) from e
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Search failed: {e.response.status_code} - {e.response.text}") from e

    async def search_dataview(self, query: str) -> list[dict[str, Any]]:
        """Perform Dataview DQL search.

        Args:
            query: Dataview query language query

        Returns:
            List of matching notes
        """
        try:
            response = await self.client.post(
                "/search/",
                content=query,
                headers={"Content-Type": "application/vnd.olrapi.dataview.dql+txt"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise TimeoutError(
                "Dataview search timed out. Try a simpler query or search fewer notes."
            ) from e
        except httpx.HTTPStatusError as e:
            raise ValueError(
                f"Dataview search failed: {e.response.status_code} - {e.response.text}. "
                f"Make sure your query syntax is valid DQL."
            ) from e

    async def search_jsonlogic(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """Perform JSONLogic search.

        Args:
            query: JSONLogic query object

        Returns:
            List of matching notes
        """
        response = await self.client.post(
            "/search/",
            json=query,
            headers={"Content-Type": "application/vnd.olrapi.jsonlogic+json"},
        )
        response.raise_for_status()
        return response.json()

    # Read operations
    async def get_note(self, path: str, as_json: bool = True) -> dict[str, Any] | str:
        """Get note content.

        Args:
            path: Path to note relative to vault root
            as_json: If True, return structured JSON with metadata; if False, return raw markdown

        Returns:
            Note content as JSON object or markdown string
        """
        headers = {}
        if as_json:
            headers["Accept"] = "application/vnd.olrapi.note+json"
        else:
            headers["Accept"] = "text/markdown"

        response = await self.client.get(f"/vault/{quote(path, safe='')}", headers=headers)
        response.raise_for_status()

        return response.json() if as_json else response.text

    async def list_vault_root(self) -> dict[str, Any]:
        """List files in vault root.

        Returns:
            Directory listing with files array
        """
        response = await self.client.get("/vault/")
        response.raise_for_status()
        return response.json()

    async def list_directory(self, path: str) -> dict[str, Any]:
        """List files in a directory.

        Args:
            path: Path to directory relative to vault root

        Returns:
            Directory listing with files array
        """
        response = await self.client.get(f"/vault/{quote(path.rstrip('/'), safe='')}/")
        response.raise_for_status()
        return response.json()

    # Periodic notes
    async def get_periodic_note(
        self,
        period: str = "daily",
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        as_json: bool = True,
    ) -> dict[str, Any] | str:
        """Get periodic note (daily, weekly, monthly, etc.).

        Args:
            period: Period type (daily, weekly, monthly, quarterly, yearly)
            year: Optional year for specific date
            month: Optional month (1-12) for specific date
            day: Optional day (1-31) for specific date
            as_json: If True, return JSON; if False, return markdown

        Returns:
            Note content
        """
        headers = {}
        if as_json:
            headers["Accept"] = "application/vnd.olrapi.note+json"
        else:
            headers["Accept"] = "text/markdown"

        if year is not None and month is not None and day is not None:
            endpoint = f"/periodic/{period}/{year}/{month}/{day}/"
        else:
            endpoint = f"/periodic/{period}/"

        response = await self.client.get(endpoint, headers=headers)
        response.raise_for_status()

        return response.json() if as_json else response.text

    # Write operations
    async def create_note(self, path: str, content: str) -> None:
        """Create or overwrite a note.

        Args:
            path: Path to note relative to vault root
            content: Markdown content
        """
        response = await self.client.put(
            f"/vault/{quote(path, safe='')}",
            content=content,
            headers={"Content-Type": "text/markdown"},
        )
        response.raise_for_status()

    async def append_to_note(self, path: str, content: str) -> None:
        """Append content to end of note.

        Args:
            path: Path to note relative to vault root
            content: Content to append
        """
        response = await self.client.post(
            f"/vault/{quote(path, safe='')}",
            content=content,
            headers={"Content-Type": "text/markdown"},
        )
        response.raise_for_status()

    async def update_section(
        self,
        path: str,
        heading: str,
        content: str,
        operation: str = "replace",
    ) -> None:
        """Update a specific section under a heading.

        Args:
            path: Path to note relative to vault root
            heading: Heading name to target (without # symbols)
            content: New content for the section
            operation: Operation type (replace, append, prepend)
        """
        try:
            response = await self.client.patch(
                f"/vault/{quote(path, safe='')}",
                content=content,
                headers={
                    "Content-Type": "text/markdown",
                    "Operation": operation,
                    "Target-Type": "heading",
                    "Target": heading,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ValueError(
                    f"Failed to update section '{heading}' in '{path}'. "
                    f"Make sure the heading exists and doesn't include # symbols. "
                    f"API response: {e.response.text}"
                ) from e
            raise

    async def update_frontmatter(
        self,
        path: str,
        key: str,
        value: str,
        operation: str = "replace",
    ) -> None:
        """Update frontmatter field.

        Args:
            path: Path to note relative to vault root
            key: Frontmatter key to update
            value: New value
            operation: Operation type (replace, append, prepend)
        """
        response = await self.client.patch(
            f"/vault/{quote(path, safe='')}",
            content=value,
            headers={
                "Content-Type": "text/markdown",
                "Operation": operation,
                "Target-Type": "frontmatter",
                "Target": key,
            },
        )
        response.raise_for_status()

    # Delete operations
    async def delete_note(self, path: str) -> None:
        """Delete a note.

        Args:
            path: Path to note relative to vault root
        """
        response = await self.client.delete(f"/vault/{quote(path, safe='')}")
        response.raise_for_status()

    # Utility operations
    async def open_note(self, path: str, new_leaf: bool = False) -> None:
        """Open a note in Obsidian UI.

        Args:
            path: Path to note relative to vault root
            new_leaf: Whether to open in a new pane
        """
        params = {"newLeaf": str(new_leaf).lower()} if new_leaf else {}
        response = await self.client.post(f"/open/{quote(path, safe='')}", params=params)
        response.raise_for_status()

    async def get_vault_info(self) -> dict[str, Any]:
        """Get vault and authentication info.

        Returns:
            Server info and auth status
        """
        response = await self.client.get("/")
        response.raise_for_status()
        return response.json()
