"""Create all database tables (idempotent).

Usage::

    python -m scripts.init_db
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make `src` importable when running as a script
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger  # noqa: E402

from src.core.config import get_settings  # noqa: E402
from src.core.database import dispose_engine, get_engine  # noqa: E402
from src.models.base import Base  # noqa: E402
# Importing the models registers them on Base.metadata
import src.models  # noqa: E402,F401


async def main() -> None:
    settings = get_settings()
    Path("./data").mkdir(parents=True, exist_ok=True)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅  Tables created for {}", settings.database.url)

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
