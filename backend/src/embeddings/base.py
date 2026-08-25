"""Embedding adapter base class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


class BaseEmbedder(ABC):
    """Generate dense vectors for a list of strings."""

    dim: int = 0
    model: str = ""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Return one vector per input text. Order is preserved."""
