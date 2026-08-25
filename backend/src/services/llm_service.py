"""LLM service: a thin façade over the active provider.

Resolves the provider on every call so a config update via ``PUT /api/config``
takes effect immediately without restarting the server.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator, List, Optional

from ..adapters.base import BaseProvider, LLMMessage
from ..adapters.factory import build_provider
from ..core.config import Settings, get_settings
from ..core.exceptions import LLMError
from ..models.config import CSConfig
from ..utils.obfuscation import deobfuscate
from sqlalchemy import select

log = logging.getLogger(__name__)


async def _load_runtime_config() -> dict:
    """Read the active CSConfig row (if any) to pick provider / model / protocol."""
    from ..core.database import session_scope

    try:
        async with session_scope() as session:
            row = (await session.execute(select(CSConfig).limit(1))).scalar_one_or_none()
            if row is None:
                return {}
            return row.data or {}
    except Exception as e:
        log.warning("Could not load CSConfig: %s", e)
        return {}


async def _build(settings: Optional[Settings] = None, override: Optional[dict] = None) -> BaseProvider:
    settings = settings or get_settings()
    runtime = await _load_runtime_config() if override is None else (override or {})

    api_key = deobfuscate(runtime.get("model_api_key") or "") or settings.llm.api_key
    base_url = runtime.get("model_base_url") or settings.llm.base_url
    model = runtime.get("model_name") or settings.llm.model
    protocol = (runtime.get("protocol") or settings.llm.protocol or "openai").lower()
    try:
        temperature = float(runtime.get("temperature", settings.llm.temperature))
    except (TypeError, ValueError):
        temperature = settings.llm.temperature
    try:
        max_tokens = int(runtime.get("max_tokens", settings.llm.max_tokens))
    except (TypeError, ValueError):
        max_tokens = settings.llm.max_tokens

    return build_provider(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        protocol=protocol,
        settings=settings,
    )


class LLMService:
    """Stateless façade: builds a provider on each call so config edits take effect."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings

    async def chat(
        self,
        messages: List[LLMMessage],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        override: Optional[dict] = None,
    ) -> str:
        provider = await _build(self._settings, override)
        try:
            return await provider.chat(messages, temperature=temperature, max_tokens=max_tokens)
        except Exception as e:
            log.exception("LLM chat failed: %s", e)
            raise LLMError(f"LLM 调用失败: {e}", details={"provider": provider.protocol}) from e
        finally:
            if hasattr(provider, "aclose"):
                await provider.aclose()  # type: ignore[attr-defined]

    async def stream_chat(
        self,
        messages: List[LLMMessage],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        override: Optional[dict] = None,
    ) -> AsyncIterator[str]:
        provider = await _build(self._settings, override)
        try:
            async for piece in provider.stream_chat(
                messages, temperature=temperature, max_tokens=max_tokens
            ):
                yield piece
        except Exception as e:
            log.exception("LLM stream failed: %s", e)
            raise LLMError(f"LLM 流式调用失败: {e}", details={"provider": provider.protocol}) from e
        finally:
            if hasattr(provider, "aclose"):
                await provider.aclose()  # type: ignore[attr-defined]

    async def test(self) -> tuple[bool, str]:
        provider = await _build(self._settings)
        try:
            return await provider.test()
        finally:
            if hasattr(provider, "aclose"):
                await provider.aclose()  # type: ignore[attr-defined]
