"""Verify Python + dependencies + config + optional services.

Exits non-zero on any required-missing problem so it can be wired into CI.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger  # noqa: E402

REQUIRED = [
    ("fastapi",        "FastAPI"),
    ("uvicorn",        "Uvicorn"),
    ("pydantic",       "Pydantic"),
    ("pydantic_settings", "Pydantic Settings"),
    ("httpx",          "HTTPX"),
    ("sqlalchemy",     "SQLAlchemy"),
    ("openpyxl",       "openpyxl (xlsx)"),
    ("docx",           "python-docx"),
]

OPTIONAL = [
    ("langchain_text_splitters", "langchain-text-splitters (falls back to built-in)"),
    ("chromadb",       "ChromaDB"),
    ("qdrant_client",  "Qdrant client"),
    ("pymilvus",       "Milvus client (pymilvus)"),
    ("milvus_lite",    "Milvus Lite (本地 .db 模式需要)"),
    ("PyPDF2",         "PyPDF2 (pdf support)"),
    ("redis",          "redis-py"),
    ("tenacity",       "tenacity"),
]


def _check(group: list[tuple[str, str]]) -> int:
    failed = 0
    for module, label in group:
        try:
            importlib.import_module(module)
            logger.info("  ✓ {}", label)
        except Exception as e:
            failed += 1
            logger.error("  ✗ {} — {}", label, e)
    return failed


def main() -> int:
    logger.info("── Required ──")
    req_failures = _check(REQUIRED)
    logger.info("── Optional ──")
    _check(OPTIONAL)

    logger.info("── Configuration ──")
    from src.core.config import get_settings
    s = get_settings()
    logger.info("  APP_ENV        = {}", s.app.env)
    logger.info("  DATABASE_URL   = {}", s.database.url)
    logger.info("  VECTOR_DB      = {}  collection={}", s.vector_db.provider, s.vector_db.collection)
    logger.info("  LLM provider   = {}  model={}  protocol={}", s.llm.provider, s.llm.model, s.llm.protocol)
    logger.info("  Embedding      = {}  model={}  dim={}", s.embedding.provider, s.embedding.model, s.embedding.dim)
    logger.info("  RAG            = top_k={}  threshold={}  chunk={}/{}",
                s.rag.top_k, s.rag.similarity_threshold, s.rag.chunk_size, s.rag.chunk_overlap)

    if not s.llm.api_key:
        logger.warning("  ⚠ LLM_API_KEY is empty — set it in .env before using chat endpoints.")
    if not s.embedding.api_key:
        logger.warning("  ⚠ EMBEDDING_API_KEY is empty — set it in .env before ingesting documents.")

    if req_failures:
        logger.error("❌ {} required package(s) missing. Run: pip install -r requirements.txt", req_failures)
        return 1
    logger.info("✅ Environment looks good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
