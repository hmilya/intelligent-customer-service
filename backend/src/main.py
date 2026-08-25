"""FastAPI application factory.

Three equivalent ways to start the server::

    python run.py                          # 推荐：项目根的一键启动脚本
    python src/main.py                     # 直接跑本文件（PyCharm ▶ 也可以）
    uvicorn src.main:app --reload          # 标准 uvicorn 命令

All routers live under ``/api/*``. CORS is permissive by default so the
embeddable widget can be loaded from any third-party site.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 支持 `python src/main.py` 直接运行：把 backend/ 加进 sys.path，
# 这样下面的 `src.xxx` 绝对导入才能找到包。
if __package__ in (None, ""):
    _BACKEND_DIR = Path(__file__).resolve().parent.parent
    if str(_BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api import admin as admin_api, chat, config, documents, models as models_api, sessions
from src.core.config import get_settings
from src.core.database import dispose_engine, get_engine
from src.core.exceptions import install_exception_handlers
from src.models.base import Base

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Ensure runtime dirs exist
    Path(settings.app.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.vector_db.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)

    # Auto-create tables on first boot. (Use Alembic in production.)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database ready: %s", settings.database.url)
    log.info("Vector DB: %s / collection=%s", settings.vector_db.provider, settings.vector_db.collection)

    yield

    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app.name,
        version="0.1.0",
        description="Document-aware multi-model customer service platform with RAG.",
        debug=settings.app.debug,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_exception_handlers(app)

    @app.middleware("http")
    async def _no_cache_frontend(request: Request, call_next):
        """Stop browsers serving a stale admin page / widget from cache.

        `no-cache` still lets a browser reuse its copy after revalidating, and
        in practice some skip the revalidation entirely — an edited widget kept
        rendering the previous build even after a hard refresh, and inside an
        iframe the parent page's refresh doesn't propagate. `no-store` removes
        the guesswork: the file is re-fetched every time.

        Cheap here (a few tens of KB, same-origin) and it eliminates a whole
        class of "I fixed it but nothing changed" confusion. If you ever serve
        the widget from a CDN, switch to a hashed filename instead.
        """
        response = await call_next(request)
        path = request.url.path
        if path.startswith(("/admin", "/widget")) or path == "/embed":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Serve admin UI and widget as static files (no separate HTTP server needed).
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    if (frontend_dir / "admin").exists():
        app.mount("/admin", StaticFiles(directory=str(frontend_dir / "admin"), html=True), name="admin")
    if (frontend_dir / "widget").exists():
        app.mount("/widget", StaticFiles(directory=str(frontend_dir / "widget"), html=True), name="widget")
    if (frontend_dir / "assets").exists():
        # Icons and donate QR codes used by the admin console.
        app.mount("/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")

    # Routers
    app.include_router(config.router,      prefix="/api/config",    tags=["config"])
    app.include_router(sessions.router,    prefix="/api/sessions",  tags=["sessions"])
    app.include_router(documents.router,   prefix="/api/documents", tags=["documents"])
    app.include_router(chat.router,        prefix="/api/chat",      tags=["chat"])
    app.include_router(models_api.router,  prefix="/api/models",    tags=["models"])
    app.include_router(admin_api.router,   prefix="/api/admin",    tags=["admin"])

    @app.get("/health", tags=["meta"])
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "name": settings.app.name, "env": settings.app.env})

    @app.get("/embed", include_in_schema=False)
    async def embed_redirect(request: Request) -> RedirectResponse:
        """Standalone chat page, for embedding via ``<iframe src=".../embed">``.

        Keeps whatever query string was passed (api, title, accent, …) so the
        host page can theme the widget.
        """
        query = request.url.query
        target = "/admin/embed.html"
        return RedirectResponse(f"{target}?{query}" if query else target)

    @app.get("/", response_class=HTMLResponse, tags=["meta"])
    async def root(request: Request) -> str:
        # Use the URL the browser actually reached us on, so the embed snippet
        # is copy-pasteable on a deployed server instead of always saying
        # localhost:8000.
        origin = f"{request.url.scheme}://{request.url.netloc}"
        return f"""
        <html><head><meta charset="utf-8"><title>{settings.app.name}</title>
        <style>body{{font-family:-apple-system,sans-serif;max-width:680px;margin:60px auto;padding:0 24px;color:#222}}
        a{{color:#0a66c2}}code{{background:#f4f4f5;padding:2px 6px;border-radius:4px;font-size:13px}}
        .card{{background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:20px;margin:16px 0}}
        .btn{{display:inline-block;background:#3b82f6;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;margin:6px 12px 6px 0;font-size:14px}}
        .btn.green{{background:#10b981}}
        .muted{{color:#6b7280;font-size:13px;line-height:1.7}}
        pre{{background:#1f2937;color:#d6deeb;padding:14px;border-radius:6px;overflow-x:auto;font-size:12.5px}}
        pre code{{background:none;color:inherit;padding:0}}
        h3{{margin-top:0}}
        ol li,ul li{{margin:6px 0}}</style></head>
        <body>
        <h1>🤖 {settings.app.name}</h1>
        <p>API: <a href="/docs">/docs</a> · <a href="/redoc">/redoc</a></p>

        <div class="card">
          <h3>🚀 快速开始</h3>
          <p>第一次使用？打开 <a href="/admin/"><strong>管理后台</strong></a>，填入 API Key 即可。</p>
          <a class="btn" href="/admin/">⚙️ 进入管理后台</a>
          <a class="btn green" href="/widget/demo/">🪟 客服组件演示</a>
        </div>

        <div class="card">
          <h3>📡 API 端点</h3>
          <ul>
          <li><code>GET  /api/config</code> · <code>PUT /api/config</code></li>
          <li><code>POST /api/documents/upload</code> · <code>POST /api/documents/process</code></li>
          <li><code>POST /api/chat/stream</code> (SSE 流式问答)</li>
          <li><code>POST /api/models/test</code> (测试模型连接)</li>
          </ul>
          <p>完整列表见 <a href="/docs">Swagger 文档</a>（共 23 个端点）</p>
        </div>

        <div class="card">
          <h3>🌐 嵌入到你的网站</h3>
          <pre><code>&lt;script src="{origin}/widget/customer-service.js?v=1"&gt;&lt;/script&gt;
&lt;script&gt;
  CustomerService.init({{
    apiUrl: "{origin}",
    accent: "#0a66c2",
    position: "right",
  }});
&lt;/script&gt;</code></pre>
          <p class="muted">
            客服名称、头像、欢迎语不用写在这里 —— 组件会自动读取
            <a href="/admin/">「客服信息」</a>的配置，改一次对所有站点生效。<br>
            <code>?v=1</code> 是缓存版本号，更新组件后递增它。
          </p>
          <p>更多方式（iframe / 小程序 / 桌面端）见 <a href="/widget/demo/embed.html">嵌入演示</a></p>
        </div>

        <div class="card">
          <h3>🚀 部署到服务器</h3>
          <p>本机跑通后，把它部署到自己的服务器对外提供服务：</p>
          <ol>
          <li><b>最快</b>：Docker Compose 一条命令起全套（应用 + MySQL + Redis + 向量库）</li>
          <li><b>常规</b>：systemd 托管 + Nginx 反向代理 + HTTPS 证书</li>
          <li><b>注意</b>：SSE 流式问答需要在 Nginx 关闭缓冲，否则回答不会逐字出现</li>
          </ol>
          <p>
            完整步骤（含 Nginx 配置、HTTPS、防火墙、备份、安全加固）见
            <b>项目根目录的 <code>docs/DEPLOYMENT.md</code></b>。
          </p>
        </div>
        </body></html>
        """

    return app


app = create_app()


def main() -> None:
    """Entry point for ``python src/main.py`` (and PyCharm's ▶ button).

    Delegates to ``run.py`` in the backend root so there's exactly one
    startup implementation (banner, dependency check, CLI flags).
    """
    backend_dir = Path(__file__).resolve().parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from run import main as run_main

    run_main()


if __name__ == "__main__":
    main()
