"""Obsidian CLI subprocess helper.

Wraps the official Obsidian CLI (requires Obsidian 1.12+ with 'obsidian' on PATH).
Uses asyncio.create_subprocess_exec (no shell) to avoid injection risks — arguments
with spaces or special characters are passed safely as discrete argv elements.
"""

import asyncio
import shutil

from pydantic import BaseModel, computed_field


class CLIResult(BaseModel):
    returncode: int
    stdout: str
    stderr: str

    @computed_field
    @property
    def ok(self) -> bool:
        # The Obsidian CLI always exits 0, even on failure — errors are
        # reported via stdout lines starting with "Error:". Check both.
        if self.returncode != 0:
            return False
        return not any(
            line.strip().startswith("Error:") for line in self.stdout.splitlines()
        )


class ObsidianCLI:
    """Wrapper for the official Obsidian CLI (Obsidian 1.12+).

    CLI availability is checked lazily on first access by looking for 'obsidian'
    on PATH. When unavailable, callers should fall back to REST API operations
    or return a descriptive error message to the user.
    """

    def __init__(self):
        self._available: bool | None = None

    @property
    def available(self) -> bool:
        """True if 'obsidian' binary is found on PATH."""
        if self._available is None:
            self._available = shutil.which("obsidian") is not None
        return self._available

    async def run(self, *args: str) -> CLIResult:
        """Run the obsidian CLI with the given arguments.

        Arguments are passed directly to execvp — no shell interpretation occurs,
        so values containing spaces, quotes, or = signs are handled correctly.
        """
        proc = await asyncio.create_subprocess_exec(
            "obsidian",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return CLIResult(
            returncode=proc.returncode if proc.returncode is not None else 0,
            stdout=stdout.decode().strip(),
            stderr=stderr.decode().strip(),
        )
