"""Document parser base class + errors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List


class DocumentParseError(Exception):
    """Raised when a document cannot be parsed."""


class Parser(ABC):
    code: str = "base"
    display_name: str = "Base"
    extensions: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, path: str | Path) -> str:
        """Return the document's plain text."""

    def parse_many(self, paths: List[str | Path]) -> str:
        """Parse and concatenate multiple files (default: join with blank line)."""
        return "\n\n".join(self.parse(p) for p in paths)
