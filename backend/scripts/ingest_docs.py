"""Bulk-ingest documents from a directory.

Usage::

    python -m scripts.ingest_docs ./samples

For each file, the script uploads → parses → chunks → embeds → stores.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger  # noqa: E402

from src.core.config import get_settings  # noqa: E402
from src.core.database import dispose_engine  # noqa: E402
from src.services.document_service import DocumentService  # noqa: E402


async def main(target: Path) -> None:
    if not target.exists():
        logger.error("Path does not exist: {}", target)
        sys.exit(1)

    settings = get_settings()
    svc = DocumentService(settings)

    files = [p for p in target.rglob("*") if p.is_file() and p.suffix.lower() in {".txt", ".docx", ".xlsx", ".pdf"}]
    logger.info("Found {} ingestible file(s) in {}", len(files), target)

    for fp in files:
        try:
            doc = await svc.ingest_path(fp)
            logger.info("  ✓ {} → {} chunks", fp.name, doc["chunk_count"])
        except Exception as e:
            logger.error("  ✗ {} — {}", fp.name, e)

    await dispose_engine()


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./samples")
    asyncio.run(main(target))
