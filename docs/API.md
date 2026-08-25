# API Reference

Base URL: `http://localhost:8000`

Interactive Swagger UI: `/docs` · ReDoc: `/redoc`

---

## Meta

### `GET /health`
```json
{ "status": "ok", "name": "IntelligentCustomerService", "env": "development" }
```

### Static pages

These are served by the backend itself — no separate web server needed.

| Path | What |
|---|---|
| `/` | Landing page with links to everything |
| `/admin/` | **Admin console** — configure everything here |
| `/admin/embed.html` | Standalone chat page |
| `/embed` | Redirect to `/admin/embed.html`, preserving the query string. Use this in `<iframe src>`. |
| `/widget/customer-service.js` | The embeddable widget (19 KB, zero deps) |
| `/widget/demo/` | Embedding demo page |
| `/docs` · `/redoc` | Swagger / ReDoc |

`/embed` accepts `?api=` `&title=` `&accent=` `&position=` `&autoOpen=` `&upload=`
so the host page can theme the widget.

---

## Admin（安装向导）

这两个端点驱动管理后台顶部的「首次运行向导」横幅。

### `GET /api/admin/status`

检查系统是否可用，返回缺什么。

```json
{
  "ready": false,
  "issues": ["客服配置未初始化"],
  "fixes": ["seed_config"],
  "details": {
    "db_ready": true,
    "has_config": false,
    "has_documents": false,
    "doc_count": 0,
    "upload_dir": "uploads",
    "upload_dir_exists": true,
    "chroma_dir": "data/chroma_db",
    "chroma_dir_exists": true,
    "vector_db_provider": "chroma",
    "llm_provider": "deepseek",
    "llm_api_key_set": true,
    "embedding_api_key_set": true
  }
}
```

`llm_api_key_set` / `embedding_api_key_set` 会同时检查 `.env` **和**数据库里的配置。

### `POST /api/admin/init`

一键初始化：建表 + 建运行目录 + 写入默认客服配置。**幂等**，可重复调用。

```bash
curl -X POST http://localhost:8000/api/admin/init
```

```json
{
  "ok": true,
  "message": "初始化完成",
  "actions": [
    "创建上传目录: uploads",
    "创建 Chroma 目录: data/chroma_db",
    "创建数据库表 (cs_config / cs_session / cs_message / cs_document)",
    "写入默认客服配置（provider: deepseek, model: deepseek-chat）"
  ],
  "details": { "tables_created": true, "seeded_config": true }
}
```

---

## Config

### `GET /api/config`
Returns the current customer-service config. All secrets (`model_api_key`,
`embedding.api_key`, `vector_db.milvus_token`) come back **masked** as
`****1234`. When no DB row exists yet, the `.env` values are surfaced instead
so the admin form isn't blank.

### `PUT /api/config`
Update config. Send the full object (do a `GET` first, spread, then modify).

**Secret handling**: leaving a secret blank *or* echoing back the `****1234`
mask keeps the stored value. Only a genuinely new string replaces it — so the
admin UI can save other fields without ever seeing the real key.

```json
{
  "name": "智能客服小助手",
  "avatar": "",
  "contact_phone": "",
  "contact_email": "",
  "welcome_message": "您好，请问有什么可以帮您？",

  "model_provider": "deepseek",
  "model_name": "deepseek-chat",
  "model_api_key": "sk-xxx",
  "model_base_url": "https://api.deepseek.com/v1",
  "protocol": "openai",
  "temperature": 0.3,
  "max_tokens": 2048,

  "embedding": {
    "provider": "openai_compatible",
    "api_key": "sk-xxx",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "text-embedding-v3",
    "dim": 1024
  },

  "vector_db": {
    "provider": "chroma",
    "host": "localhost",
    "port": 6333,
    "collection": "knowledge_base",
    "embedding_dimension": 1024,
    "persist_directory": "./data/chroma_db",
    "milvus_uri": "./data/milvus.db",
    "milvus_token": "",
    "milvus_db_name": ""
  },

  "rag": {
    "top_k": 5,
    "similarity_threshold": 0.5,
    "chunk_size": 500,
    "chunk_overlap": 100,
    "chunk_strategy": "structure",
    "chunk_prefix_heading": true
  },

  "active_provider_code": "deepseek"
}
```

Changes take effect on the next request — no restart needed. (Switching
`vector_db.provider` does require a restart plus re-ingesting documents.)

### `GET /api/config/providers`

Returns the vendor registry (15 entries). Each entry:

```json
{
  "code": "volcengine_plan",
  "display_name": "火山方舟 · 包月套餐（Coding Plan）",
  "protocols": ["openai", "anthropic"],
  "endpoints": [
    { "protocol": "openai",    "base_url": "https://ark.cn-beijing.volces.com/api/plan/v3", "default_model": "ark-code-latest" },
    { "protocol": "anthropic", "base_url": "https://ark.cn-beijing.volces.com/api/plan/v1", "default_model": "ark-code-latest" }
  ],
  "default_embedding_model": "",
  "recommended_models": ["ark-code-latest"],
  "supports_model_listing": false,
  "notes": "包月套餐专用地址…",
  "is_custom": false,
  "verified": true
}
```

| Field | Meaning |
|---|---|
| `endpoints` | One entry per protocol the vendor speaks. Switching protocol in the UI swaps `base_url` + `default_model` from here. |
| `recommended_models` | Curated fallback list, used when `/api/models/available` can't reach the vendor. |
| `supports_model_listing` | `false` → don't even try `GET {base}/models`. |
| `is_custom` | `true` → the UI must ask for `base_url` and `model` (no presets). |
| `verified` | `false` → preset values are **unconfirmed**; the UI shows an orange warning. |

Legacy codes (`qwen`, `bailian`, `doubao`, `volcengine`, `volcengine_ark`,
`volcengine_anthropic`) are transparently mapped onto their current entries, so
configs saved by older versions keep working.

---

## Documents

### `POST /api/documents/upload`
Multipart upload. Accepts `.txt`, `.docx`, `.xlsx`, `.pdf` (max 20 MB).

```bash
curl -F "file=@samples/产品手册.txt" http://localhost:8000/api/documents/upload
```

Response:
```json
{
  "id": "a1b2c3...",
  "filename": "产品手册.txt",
  "file_size": 12345,
  "file_md5": "...",
  "mime_type": "text/plain",
  "parser_code": "txt",
  "status": "uploaded",
  "chunk_count": 0
}
```

### `POST /api/documents/process`
Triggers chunking + embedding + indexing.

```bash
curl -X POST http://localhost:8000/api/documents/process \
  -H "Content-Type: application/json" \
  -d '{"document_id": "a1b2c3...", "chunk_size": 500, "chunk_overlap": 100}'
```

### `GET /api/documents/list`
Returns all uploaded documents with status.

### `DELETE /api/documents/{id}`
Removes the document and its vectors.

### `GET /api/documents/parsers`
Returns supported file formats.

### `POST /api/documents/split-preview`

Chunk text **without** embedding or indexing it — used by the admin UI to let
you tune chunk size / strategy and see the result immediately.

Pass either `text` (pasted) or `document_id` (already uploaded):

```bash
curl -X POST http://localhost:8000/api/documents/split-preview \
  -H "Content-Type: application/json" \
  -d '{"document_id": "abc123", "strategy": "structure"}'
```

| Field | Default | Meaning |
|---|---|---|
| `text` | — | Raw text to split |
| `document_id` | — | Split an uploaded document instead |
| `chunk_size` / `chunk_overlap` | saved config | Override for this preview only |
| `strategy` | saved config | `structure` \| `window` |
| `prefix_heading` | saved config | Prepend the heading path to each chunk |

Response:

```json
{
  "source": "sample_knowledge.txt",
  "strategy": "structure",
  "chunk_size": 500,
  "chunk_overlap": 100,
  "prefix_heading": true,
  "total_chars": 595,
  "chunk_count": 6,
  "avg_chars": 97,
  "min_chars": 9,
  "max_chars": 260,
  "chunks": [
    { "index": 2, "heading": "保修条款", "chars": 105, "text": "【保修条款】\n1. 整机保修期为 12 个月…" }
  ],
  "truncated": false
}
```

At most 60 chunks are returned; `truncated` says whether more exist.

---

## Chat

### `POST /api/chat`
Non-streaming RAG chat.

```json
{
  "session_id": "optional-id",
  "message": "产品的保修期是多久？",
  "agent_name": "智能客服小助手"
}
```

Response:
```json
{
  "session_id": "...",
  "answer": "根据资料 [1]，保修期为 12 个月。",
  "sources": [
    {
      "index": 1,
      "chunk_id": "abc123:2",
      "text": "【保修条款】\n1. 整机保修期为 12 个月…",
      "score": 0.7907,
      "document_id": "abc123",
      "filename": "sample_knowledge.txt",
      "heading": "保修条款",
      "chunk_index": 2
    }
  ]
}
```

`score` is normalised to `0..1` across all three vector stores, so the
similarity threshold means the same thing regardless of backend.
`heading` is the section the chunk came from (empty when the document has no
recognisable structure).

### `POST /api/chat/stream`
Server-Sent Events stream of the same call.

SSE events:
- `event: meta` — first, carries `{session_id}`
- `event: token` — incremental text `{text}`
- `event: sources` — final, the matched chunks array
- `event: done` — stream end `{ok: true|false}`
- `event: error` — on failure `{message}`

```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"产品的保修期是多久？"}'
```

---

## Sessions

### `POST /api/sessions`
Create a session. Body: `{user_id?, title?, meta?}`.

### `GET /api/sessions?user_id=&limit=`
List sessions.

### `GET /api/sessions/{id}`
Get one session.

### `POST /api/sessions/{id}/close`
Mark a session as closed.

### `GET /api/sessions/{id}/messages?limit=200`
Get all messages in a session.

---

## Models

### `GET /api/models`
Returns both LLM providers and vector DB providers.

### `GET /api/models/vector-db`
Returns vector DB providers only.

### `POST /api/models/test`
Smoke-test the LLM connection. Accepts any of:
`{provider?, model?, api_key?, base_url?, protocol?}`. Missing fields fall back to the active `CSConfig`.

```bash
curl -X POST http://localhost:8000/api/models/test \
  -H "Content-Type: application/json" \
  -d '{"provider": "deepseek", "api_key": "sk-xxx", "model": "deepseek-chat"}'
```

Response:
```json
{ "ok": true, "message": "测试成功 - 模型回复: OK" }
```

### `POST /api/models/test-embedding`

Embed a probe string and report the **actual vector dimension** — use this to
get the number that `VECTOR_DB_EMBEDDING_DIM` must match.

```bash
curl -X POST http://localhost:8000/api/models/test-embedding \
  -H "Content-Type: application/json" -d '{}'
```

```json
{
  "ok": true,
  "message": "测试成功 - 模型 text-embedding-v3 返回 1024 维向量",
  "dim": 1024,
  "configured_dim": 1024
}
```

If `dim != configured_dim` the message warns you, and the admin UI
auto-corrects both the embedding and vector-DB dimension settings.

Omitted fields (`api_key` / `base_url` / `model`) fall back to the saved config.

### `POST /api/models/available`

List the models a vendor actually offers, by calling its `GET {base}/models`.

```bash
curl -X POST http://localhost:8000/api/models/available \
  -H "Content-Type: application/json" \
  -d '{"provider": "dashscope", "protocol": "openai"}'
```

```json
{
  "ok": true,
  "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
  "source": "api",
  "message": "已从厂商接口获取 42 个模型"
}
```

`source` tells you where the list came from:

| `source` | When |
|---|---|
| `api` | Fetched live from the vendor |
| `recommended` | Fell back to the built-in curated list — missing key, vendor has no listing endpoint, or the call failed. `message` explains which. |

Chat models are sorted first; embedding / tts / whisper / image entries are
pushed to the end. This endpoint **never fails hard** — it always returns a
usable list so the UI dropdown is never empty.

---

## Error envelope

All errors use:
```json
{
  "error": {
    "code": "document_error",
    "message": "Unsupported file type: foo.exe",
    "details": {}
  }
}
```

| HTTP | code                | When |
|------|---------------------|------|
| 400  | `document_error`    | Bad file / unsupported type |
| 404  | `not_found`         | Missing session / document |
| 422  | `validation_error`  | Bad input shape |
| 500  | `vector_store_error` / `internal_error` | Server-side issue |
| 502  | `llm_error` / `embedding_error` | Upstream API failure |
