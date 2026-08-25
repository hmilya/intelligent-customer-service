"""Seed default customer-service config + AI provider list into the DB.

This is optional — the API also works without seeding. The script is useful
for the admin UI to start with sensible defaults.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger  # noqa: E402
from sqlalchemy import select  # noqa: E402

from src.core.config import get_settings  # noqa: E402
from src.core.database import dispose_engine, session_scope  # noqa: E402
from src.core.registry import AI_PROVIDERS, get_provider  # noqa: E402
from src.models.config import CSConfig  # noqa: E402


async def seed_config() -> None:
    settings = get_settings()
    provider = get_provider(settings.llm.provider) or AI_PROVIDERS[0]
    base_url = settings.llm.base_url or provider.base_url
    model = settings.llm.model or provider.default_model
    protocol = settings.llm.protocol

    default = {
        "name": "智能客服小助手",
        "avatar": "",
        "contact_phone": "",
        "contact_email": "",
        "welcome_message": "您好，请问有什么可以帮您？",
        "model_provider": provider.code,
        "model_name": model,
        "model_api_key": settings.llm.api_key,
        "model_base_url": base_url,
        "protocol": protocol,
        "temperature": settings.llm.temperature,
        "max_tokens": settings.llm.max_tokens,
        "vector_db": {
            "provider": settings.vector_db.provider,
            "host": settings.vector_db.host,
            "port": settings.vector_db.port,
            "collection": settings.vector_db.collection,
            "embedding_dimension": settings.vector_db.embedding_dim,
            "persist_directory": settings.vector_db.chroma_persist_dir,
        },
        "rag": {
            "top_k": settings.rag.top_k,
            "similarity_threshold": settings.rag.similarity_threshold,
            "chunk_size": settings.rag.chunk_size,
            "chunk_overlap": settings.rag.chunk_overlap,
        },
        "active_provider_code": provider.code,
    }

    async with session_scope() as session:
        existing = await session.execute(select(CSConfig).limit(1))
        row = existing.scalar_one_or_none()
        if row is None:
            session.add(CSConfig(data=default))
            logger.info("✅ Inserted default CSConfig")
        else:
            # Soft merge: keep existing data, only set if missing.
            merged = {**default, **row.data}
            row.data = merged
            logger.info("✅ Refreshed existing CSConfig (kept overrides)")


async def main() -> None:
    await seed_config()
    logger.info("Provider registry has {} entries:", len(AI_PROVIDERS))
    for p in AI_PROVIDERS:
        logger.info("  - {:<22} {:<10} {}", p.code, p.protocol, p.display_name)
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
