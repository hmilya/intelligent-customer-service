"""Document metadata ORM (uploaded knowledge files)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Document(Base):
    __tablename__ = "cs_document"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    file_md5: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    parser_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="uploaded", nullable=False)
    # uploaded → processing → ready → failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Progress during ingestion: how many chunks have been embedded so far.
    # Lets the UI show "132/742" instead of a spinner that might be lying.
    chunks_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunks_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    chunk_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_overlap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "file_size": self.file_size,
            "file_md5": self.file_md5,
            "mime_type": self.mime_type,
            "parser_code": self.parser_code,
            "status": self.status,
            "chunk_count": self.chunk_count,
            "chunks_done": self.chunks_done,
            "chunks_total": self.chunks_total,
            "error_message": self.error_message,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
