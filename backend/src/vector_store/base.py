"""Vector store base + shared types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class VectorStoreError(Exception):
    """Raised when the vector store fails."""


@dataclass
class ChunkRecord:
    """A single chunk to be embedded and indexed."""
    chunk_id: str             # globally unique, e.g. {doc_id}:{index}
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorHit:
    """A single retrieval hit."""
    chunk_id: str
    text: str
    score: float              # higher is more similar (0..1 after normalization)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseVectorStore(ABC):
    """Pluggable vector store. Implementations: Chroma, Qdrant."""

    name: str = "base"

    @abstractmethod
    async def add(
        self,
        document_id: str,
        chunks: List[ChunkRecord],
        vectors: List[List[float]],
    ) -> int:
        """Add (or upsert) chunks. Returns count indexed."""

    @abstractmethod
    async def query(
        self,
        vector: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[VectorHit]:
        """Return up to ``top_k`` hits above ``threshold``."""

    @abstractmethod
    async def delete_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document. Returns count removed."""

    @abstractmethod
    async def count(self) -> int:
        """Total number of chunks indexed."""

    @abstractmethod
    async def aclose(self) -> None:
        """Release any held resources."""
