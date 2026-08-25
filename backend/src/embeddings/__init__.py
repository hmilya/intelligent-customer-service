"""Embeddings package."""
from .base import BaseEmbedder, EmbeddingError
from .openai_compatible_embedder import OpenAICompatibleEmbedder

__all__ = ["BaseEmbedder", "EmbeddingError", "OpenAICompatibleEmbedder"]
