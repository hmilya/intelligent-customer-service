"""Customer-service configuration API."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.exceptions import NotFoundError
from ..core.registry import list_providers
from ..models.config import CSConfig
from ..utils.obfuscation import deobfuscate, obfuscate

router = APIRouter()


class VectorDBConfigIn(BaseModel):
    provider: str = "chroma"
    host: str = "localhost"
    port: int = 6333
    collection: str = "knowledge_base"
    embedding_dimension: int = 1024
    persist_directory: str = "./data/chroma_db"
    # Milvus-specific (ignored by the other providers)
    milvus_uri: str = "./data/milvus.db"
    milvus_token: str = ""
    milvus_db_name: str = ""


class RAGConfigIn(BaseModel):
    top_k: int = 5
    similarity_threshold: float = 0.5
    chunk_size: int = 500
    chunk_overlap: int = 100
    chunk_strategy: str = "structure"      # structure | window
    chunk_prefix_heading: bool = True
    # False → refuse when nothing relevant is retrieved (traceable answers).
    # True  → fall back to the model's own knowledge.
    allow_model_knowledge: bool = False
    # Score above which retrieved chunks count as actually answering the
    # question (only used when allow_model_knowledge is on).
    relevance_threshold: float = 0.76


class EmbeddingConfigIn(BaseModel):
    provider: str = "openai_compatible"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    dim: int = 1024


class CSConfigIn(BaseModel):
    name: str = "智能客服小助手"
    avatar: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    welcome_message: str = "您好，请问有什么可以帮您？"
    model_provider: str = "deepseek"
    model_name: str = "deepseek-chat"
    model_api_key: str = ""
    model_base_url: str = ""
    protocol: str = "openai"
    temperature: float = 0.3
    max_tokens: int = 2048
    embedding: EmbeddingConfigIn = Field(default_factory=EmbeddingConfigIn)
    vector_db: VectorDBConfigIn = Field(default_factory=VectorDBConfigIn)
    rag: RAGConfigIn = Field(default_factory=RAGConfigIn)
    active_provider_code: Optional[str] = None


MASK_PREFIX = "****"


def _mask(raw: str) -> str:
    if not raw:
        return ""
    return MASK_PREFIX + raw[-4:] if len(raw) > 4 else MASK_PREFIX


def _is_masked(value: str) -> bool:
    """True if the value is a placeholder the UI echoed back, not a real secret."""
    return bool(value) and value.startswith(MASK_PREFIX)


class CSConfigOut(CSConfigIn):
    model_api_key: str = ""  # masked in responses

    @classmethod
    def from_data(cls, data: Dict[str, Any], *, mask_key: bool = True) -> "CSConfigOut":
        d = dict(data or {})

        # LLM key
        raw_key = deobfuscate(d.get("model_api_key") or "")
        d["model_api_key"] = (_mask(raw_key) if mask_key else raw_key) if raw_key else ""

        # Embedding key (nested)
        emb = dict(d.get("embedding") or {})
        raw_emb = deobfuscate(emb.get("api_key") or "")
        emb["api_key"] = (_mask(raw_emb) if mask_key else raw_emb) if raw_emb else ""
        d["embedding"] = emb

        # Milvus token (nested)
        vec = dict(d.get("vector_db") or {})
        raw_tok = deobfuscate(vec.get("milvus_token") or "")
        vec["milvus_token"] = (_mask(raw_tok) if mask_key else raw_tok) if raw_tok else ""
        d["vector_db"] = vec

        # Strip unknown top-level fields
        for k in list(d.keys()):
            if k not in cls.model_fields:
                d.pop(k, None)

        # Map legacy/merged provider codes onto their current entry so the UI
        # dropdown can select them (e.g. "qwen" → "dashscope").
        from ..core.registry import resolve_provider_code

        if d.get("model_provider"):
            d["model_provider"] = resolve_provider_code(d["model_provider"])
        if d.get("active_provider_code"):
            d["active_provider_code"] = resolve_provider_code(d["active_provider_code"])

        return cls(**d)


@router.get("", response_model=CSConfigOut, summary="Get customer-service config")
async def get_config(db: AsyncSession = Depends(get_db)) -> CSConfigOut:
    row = (await db.execute(select(CSConfig).limit(1))).scalar_one_or_none()
    if row is None:
        return _config_with_env_defaults()
    return CSConfigOut.from_data(row.data or {}, mask_key=True)


def _config_with_env_defaults() -> CSConfigOut:
    """No DB row yet — surface the .env values so the UI isn't blank."""
    from ..core.config import get_settings
    from ..core.registry import get_provider

    s = get_settings()
    spec = get_provider(s.llm.provider)
    return CSConfigOut(
        model_provider=s.llm.provider,
        model_name=s.llm.model or (spec.default_model if spec else ""),
        model_api_key=_mask(s.llm.api_key),
        model_base_url=s.llm.base_url or (spec.base_url if spec else ""),
        protocol=s.llm.protocol,
        temperature=s.llm.temperature,
        max_tokens=s.llm.max_tokens,
        embedding=EmbeddingConfigIn(
            provider=s.embedding.provider,
            api_key=_mask(s.embedding.api_key),
            base_url=s.embedding.base_url,
            model=s.embedding.model,
            dim=s.embedding.dim,
        ),
        vector_db=VectorDBConfigIn(
            provider=s.vector_db.provider,
            host=s.vector_db.host,
            port=s.vector_db.port,
            collection=s.vector_db.collection,
            embedding_dimension=s.vector_db.embedding_dim,
            persist_directory=s.vector_db.chroma_persist_dir,
            milvus_uri=s.vector_db.milvus_uri,
            milvus_db_name=s.vector_db.milvus_db_name,
        ),
        rag=RAGConfigIn(
            top_k=s.rag.top_k,
            similarity_threshold=s.rag.similarity_threshold,
            chunk_size=s.rag.chunk_size,
            chunk_overlap=s.rag.chunk_overlap,
        ),
        active_provider_code=s.llm.provider,
    )


@router.put("", response_model=CSConfigOut, summary="Update customer-service config")
async def put_config(body: CSConfigIn, db: AsyncSession = Depends(get_db)) -> CSConfigOut:
    row = (await db.execute(select(CSConfig).limit(1))).scalar_one_or_none()
    data = body.model_dump()
    previous = row.data if row is not None else {}

    def resolve_secret(incoming: str, prev_obfuscated: str) -> str:
        """Keep the stored secret when the UI echoes back a mask or blank."""
        incoming = (incoming or "").strip()
        if not incoming or _is_masked(incoming):
            return prev_obfuscated or ""
        return obfuscate(incoming)

    # LLM key
    data["model_api_key"] = resolve_secret(
        data.get("model_api_key", ""), (previous or {}).get("model_api_key", "")
    )

    # Embedding key
    emb = dict(data.get("embedding") or {})
    prev_emb = dict((previous or {}).get("embedding") or {})
    emb["api_key"] = resolve_secret(emb.get("api_key", ""), prev_emb.get("api_key", ""))
    data["embedding"] = emb

    # Milvus token
    vec = dict(data.get("vector_db") or {})
    prev_vec = dict((previous or {}).get("vector_db") or {})
    vec["milvus_token"] = resolve_secret(
        vec.get("milvus_token", ""), prev_vec.get("milvus_token", "")
    )
    data["vector_db"] = vec

    if row is None:
        row = CSConfig(data=data)
        db.add(row)
    else:
        row.data = data
    await db.flush()
    return CSConfigOut.from_data(row.data or {}, mask_key=True)


@router.get("/providers", summary="List supported LLM providers")
async def list_llm_providers() -> dict:
    return {"providers": list_providers()}
