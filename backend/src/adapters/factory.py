"""LLM provider factory: dispatch by protocol."""
from __future__ import annotations

from typing import Optional

from ..core.config import Settings, get_settings
from ..core.exceptions import LLMError
from .anthropic_adapter import AnthropicStyleProvider
from .base import BaseProvider, LLMConfig
from .openai_adapter import OpenAIStyleProvider


def build_provider(
    *,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2048,
    protocol: str = "openai",
    extra: Optional[dict] = None,
    settings: Optional[Settings] = None,
) -> BaseProvider:
    """Build a provider. If any of the explicit args is empty, fall back to settings."""
    settings = settings or get_settings()
    cfg = LLMConfig(
        api_key=api_key or settings.llm.api_key,
        base_url=base_url or settings.llm.base_url,
        model=model or settings.llm.model,
        temperature=temperature if temperature is not None else settings.llm.temperature,
        max_tokens=max_tokens or settings.llm.max_tokens,
        extra=extra or {},
    )
    if not cfg.api_key:
        raise LLMError(
            "LLM_API_KEY is empty. Set it in .env or in the customer-service config.",
            details={"protocol": protocol, "model": cfg.model},
        )
    if protocol == "anthropic":
        return AnthropicStyleProvider(cfg)
    if protocol == "openai":
        return OpenAIStyleProvider(cfg)
    raise LLMError(f"Unsupported LLM protocol: {protocol}")
