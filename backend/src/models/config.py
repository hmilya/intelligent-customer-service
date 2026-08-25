"""Customer-service configuration (single-row table)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import JSON, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CSConfig(Base):
    """A single-row table holding the editable customer-service configuration.

    The whole configuration is a JSON blob so the schema can evolve without
    migrations; in production you'd split hot fields into typed columns.
    """

    __tablename__ = "cs_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.data
