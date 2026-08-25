"""ChromaDB-backed vector store.

Uses persistent local storage by default (``PersistentClient``) and runs
inside an ``asyncio.to_thread`` shim so the blocking Chroma API doesn't
stall the event loop. Cosine similarity is the default distance metric;
we convert to a 0..1 score by ``1 - distance``.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseVectorStore, ChunkRecord, VectorHit, VectorStoreError

log = logging.getLogger(__name__)


def _to_thread(func, /, *args, **kwargs):
    return asyncio.get_running_loop().run_in_executor(None, lambda: func(*args, **kwargs))


class ChromaStore(BaseVectorStore):
    name = "chroma"

    def __init__(
        self,
        persist_dir: str | Path,
        collection: str,
        embedding_dim: int = 0,
    ) -> None:
        try:
            import chromadb  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise VectorStoreError("chromadb is not installed. `pip install chromadb`") from e

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection
        self.embedding_dim = embedding_dim

        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("ChromaStore ready: dir=%s collection=%s", self.persist_dir, collection)

    @staticmethod
    def _distance_to_score(distance: float) -> float:
        # cosine distance in [0, 2] -> similarity in [-1, 1]; map to [0, 1]
        sim = 1.0 - float(distance)
        return max(0.0, min(1.0, (sim + 1.0) / 2.0))

    async def add(
        self,
        document_id: str,
        chunks: List[ChunkRecord],
        vectors: List[List[float]],
    ) -> int:
        if not chunks:
            return 0
        if len(chunks) != len(vectors):
            raise VectorStoreError(
                f"chunks/vectors length mismatch: {len(chunks)} vs {len(vectors)}"
            )
        ids = [c.chunk_id for c in chunks]
        docs = [c.text for c in chunks]
        metas: List[Dict[str, Any]] = []
        for c in chunks:
            m = dict(c.metadata or {})
            m.setdefault("document_id", document_id)
            metas.append(m)

        def _do():
            self._collection.upsert(ids=ids, documents=docs, embeddings=vectors, metadatas=metas)
            return len(ids)

        return await _to_thread(_do)

    async def query(
        self,
        vector: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[VectorHit]:
        if not vector:
            return []

        def _do():
            kwargs: Dict[str, Any] = {"query_embeddings": [vector], "n_results": max(1, top_k)}
            if where:
                kwargs["where"] = where
            return self._collection.query(**kwargs)

        res = await _to_thread(_do)
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]

        hits: List[VectorHit] = []
        for cid, doc, dist, meta in zip(ids, docs, dists, metas):
            score = self._distance_to_score(dist)
            if score < threshold:
                continue
            hits.append(VectorHit(chunk_id=cid, text=doc or "", score=score, metadata=meta or {}))
        return hits

    async def delete_document(self, document_id: str) -> int:
        def _do():
            existing = self._collection.get(where={"document_id": document_id})
            ids = existing.get("ids") or []
            if ids:
                self._collection.delete(ids=ids)
            return len(ids)

        return await _to_thread(_do)

    async def count(self) -> int:
        def _do():
            return self._collection.count()

        return int(await _to_thread(_do))

    async def aclose(self) -> None:
        # Chroma doesn't need an explicit close; we drop references.
        self._collection = None  # type: ignore[assignment]
        self._client = None  # type: ignore[assignment]
