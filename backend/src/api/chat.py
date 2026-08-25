"""Chat API: non-streaming /chat and streaming /chat/stream (SSE)."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.base import LLMMessage
from ..core.config import get_settings
from ..core.database import get_db
from ..core.exceptions import LLMError
from ..services.rag_service import RAGService
from ..services.session_service import SessionService
from ..utils.sse import sse_pack

log = logging.getLogger(__name__)
router = APIRouter()


# ----- Schemas ---------------------------------------------------------
class ChatIn(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    agent_name: Optional[str] = None
    history: Optional[List[dict]] = None  # optional override; else loaded from session


class ChatOut(BaseModel):
    session_id: str
    answer: str
    sources: list = Field(default_factory=list)


# ----- Helpers ---------------------------------------------------------
def _sse(event: str, data, *, id: Optional[str] = None) -> bytes:
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False, default=str)
    return sse_pack(event, data, id=id)


def _history_to_llm(history: List[dict]) -> List[LLMMessage]:
    out: List[LLMMessage] = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant", "system") and isinstance(content, str):
            out.append(LLMMessage(role=role, content=content))
    return out


# ----- Endpoints -------------------------------------------------------
@router.post("", response_model=ChatOut, summary="One-shot RAG chat (JSON)")
async def chat(body: ChatIn, db: AsyncSession = Depends(get_db)) -> ChatOut:
    settings = get_settings()
    session_svc = SessionService(db)

    session_id = body.session_id
    if not session_id:
        sess = await session_svc.create_session(title=body.message[:30] or "新会话")
        session_id = sess.id

    # Persist user turn
    await session_svc.add_message(session_id, "user", body.message)

    history_llm: List[LLMMessage] = []
    if body.history:
        history_llm = _history_to_llm(body.history)
    else:
        history_llm = await session_svc.build_history(session_id)

    rag = RAGService(settings)
    try:
        answer, sources = await rag.ask(
            body.message, history=history_llm, agent_name=body.agent_name or "智能客服小助手"
        )
    except LLMError as e:
        raise
    finally:
        await rag.aclose()

    await session_svc.add_message(session_id, "assistant", answer, sources=sources)
    return ChatOut(session_id=session_id, answer=answer, sources=sources)


@router.post("/stream", summary="Streaming RAG chat via SSE")
async def chat_stream(body: ChatIn, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Server-Sent Events stream. Events:

      - ``meta``   : first, carries ``{session_id}``
      - ``token``  : incremental text from the LLM
      - ``sources``: final event, carries the matched chunks
      - ``done``   : end of stream
      - ``error``  : on failure, carries the error message
    """
    settings = get_settings()
    session_svc = SessionService(db)

    async def gen() -> AsyncIterator[bytes]:
        session_id = body.session_id
        if not session_id:
            sess = await session_svc.create_session(title=body.message[:30] or "新会话")
            session_id = sess.id

        yield _sse("meta", {"session_id": session_id})
        await session_svc.add_message(session_id, "user", body.message)

        history_llm: List[LLMMessage] = []
        if body.history:
            history_llm = _history_to_llm(body.history)
        else:
            history_llm = await session_svc.build_history(session_id)

        rag = RAGService(settings)
        answer_parts: List[str] = []
        sources_payload: Optional[list] = None
        try:
            async for token, sources in rag.stream_ask(
                body.message,
                history=history_llm,
                agent_name=body.agent_name or "智能客服小助手",
            ):
                if sources is not None:
                    sources_payload = sources
                elif token:
                    answer_parts.append(token)
                    yield _sse("token", {"text": token})

            full_answer = "".join(answer_parts) or (sources_payload and "") or ""
            if sources_payload is None:
                # stream_ask guarantees a final event; safety net
                sources_payload = []
            yield _sse("sources", sources_payload)
            yield _sse("done", {"ok": True})
            await session_svc.add_message(session_id, "assistant", full_answer, sources=sources_payload)
        except Exception as e:
            log.exception("chat stream failed: %s", e)
            yield _sse("error", {"message": str(e)})
            yield _sse("done", {"ok": False})
            try:
                await session_svc.add_message(
                    session_id, "assistant", f"[错误] {e}", meta={"error": True}
                )
            except Exception:
                pass
        finally:
            await rag.aclose()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering
        },
    )
