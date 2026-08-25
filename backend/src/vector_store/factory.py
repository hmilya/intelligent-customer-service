"""Vector store factory: pick Chroma, Qdrant or Milvus from settings."""
from __future__ import annotations

from typing import Optional

from ..core.config import Settings, get_settings
from ..core.exceptions import VectorStoreError
from .base import BaseVectorStore
from .chroma_store import ChromaStore
from .milvus_store import MilvusStore
from .qdrant_store import QdrantStore


def build_vector_store(settings: Optional[Settings] = None) -> BaseVectorStore:
    settings = settings or get_settings()
    v = settings.vector_db
    if v.provider == "chroma":
        return ChromaStore(
            persist_dir=v.chroma_persist_dir,
            collection=v.collection,
            embedding_dim=v.embedding_dim,
        )
    if v.provider == "qdrant":
        return QdrantStore(
            host=v.host,
            port=v.port,
            collection=v.collection,
            embedding_dim=v.embedding_dim,
        )
    if v.provider == "milvus":
        return MilvusStore(
            collection=v.collection,
            embedding_dim=v.embedding_dim,
            uri=v.milvus_uri,
            host=v.host,
            port=v.milvus_port,
            token=v.milvus_token,
            db_name=v.milvus_db_name,
        )
    raise VectorStoreError(f"Unsupported vector DB provider: {v.provider}")
