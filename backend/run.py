#!/usr/bin/env python3
"""一键启动智能客服系统。

在 PyCharm 里直接右键此文件 → Run，或在终端执行::

    python run.py

启动后浏览器打开 http://localhost:8000/admin/ 即可完成全部配置
（首次运行会在页面顶部提示「一键初始化」，点一下就好，无需执行任何脚本）。

可选参数::

    python run.py --port 9000        # 换端口
    python run.py --no-reload        # 关闭热重载
    python run.py --host 0.0.0.0     # 允许局域网访问
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import webbrowser
from pathlib import Path
from threading import Timer

# 让 `src` 包可以被导入（相当于把 backend/ 加进 sys.path）
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _check_deps(auto_install: bool = False) -> None:
    """启动前检查关键依赖。

    缺依赖时给出**当前解释器对应**的安装命令（避免 PyCharm 用了另一个
    venv、却照着提示往系统 Python 里装的坑）。``auto_install=True`` 时
    直接调 pip 装好再继续。
    """
    # (import 名, pip 包名)
    required = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn[standard]"),
        ("pydantic_settings", "pydantic-settings"),
        ("sqlalchemy", "sqlalchemy"),
        ("greenlet", "greenlet"),
        ("aiosqlite", "aiosqlite"),
        ("httpx", "httpx"),
        ("multipart", "python-multipart"),
        ("tenacity", "tenacity"),
        ("loguru", "loguru"),
    ]
    missing = [pip_name for module, pip_name in required if not _can_import(module)]
    if not missing:
        return

    req_file = BACKEND_DIR / "requirements.txt"

    if auto_install:
        print("=" * 62, flush=True)
        print(f"  📦 检测到缺少依赖：{', '.join(missing)}", flush=True)
        print(f"  正在使用 {sys.executable} 自动安装…", flush=True)
        print("=" * 62, flush=True)
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        rc = subprocess.call(cmd)
        if rc != 0:
            print("\n  ❌ 自动安装失败，请手动执行上面的命令。", flush=True)
            sys.exit(1)
        still_missing = [p for m, p in required if not _can_import(m)]
        if still_missing:
            print(f"\n  ❌ 安装后仍缺少：{', '.join(still_missing)}", flush=True)
            sys.exit(1)
        print("\n  ✅ 依赖安装完成，继续启动…\n", flush=True)
        return

    # 不自动装：打印精确到当前解释器的命令
    print("=" * 62, flush=True)
    print("  ❌ 缺少依赖，无法启动", flush=True)
    print("=" * 62, flush=True)
    print(f"  当前解释器：{sys.executable}", flush=True)
    print(f"  缺少的包　：{', '.join(missing)}", flush=True)
    print("-" * 62, flush=True)
    print("  请执行下面**任意一条**命令安装：", flush=True)
    print(flush=True)
    print(f"    {sys.executable} -m pip install -r {req_file}", flush=True)
    print(flush=True)
    print("  或者让本脚本自动安装：", flush=True)
    print(flush=True)
    print(f"    {sys.executable} {Path(__file__).name} --install", flush=True)
    print("=" * 62, flush=True)
    sys.exit(1)


def _can_import(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _banner(settings, host: str, port: int, reload_enabled: bool) -> None:
    shown_host = "localhost" if host in ("0.0.0.0", "127.0.0.1") else host
    lines = [
        "",
        "=" * 62,
        f"  🤖 {settings.app.name}",
        "=" * 62,
        f"  ⚙️  管理后台   http://{shown_host}:{port}/admin/     ← 从这里开始",
        f"  🪟  组件演示   http://{shown_host}:{port}/widget/demo/",
        f"  📖  API 文档   http://{shown_host}:{port}/docs",
        "-" * 62,
        f"  环境         {settings.app.env}    热重载: {'开' if reload_enabled else '关'}",
        f"  数据库       {settings.database.url}",
        f"  向量库       {settings.vector_db.provider} / {settings.vector_db.collection}",
        f"  对话模型     {settings.llm.provider} / {settings.llm.model} ({settings.llm.protocol})",
        f"  向量模型     {settings.embedding.provider} / {settings.embedding.model}",
        "-" * 62,
    ]
    if not settings.llm.api_key:
        lines.append("  ⚠  尚未配置对话模型 API Key")
    if not settings.embedding.api_key:
        lines.append("  ⚠  尚未配置向量模型 API Key")
    if not settings.llm.api_key or not settings.embedding.api_key:
        lines.append("     → 打开管理后台「模型配置」填写即可，无需改文件")
    else:
        lines.append("  ✅ API Key 已配置")
    lines += ["=" * 62, ""]

    # flush 一次性写出，避免和 uvicorn 的 stderr 日志交错
    print("\n".join(lines), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="启动智能客服系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default=None, help="监听地址（默认读 .env 的 APP_HOST）")
    parser.add_argument("--port", type=int, default=None, help="监听端口（默认读 .env 的 APP_PORT）")
    parser.add_argument("--no-reload", action="store_true", help="关闭代码热重载")
    parser.add_argument("--reload", action="store_true", help="强制开启代码热重载")
    parser.add_argument("--open", action="store_true", help="启动后自动打开浏览器到管理后台")
    parser.add_argument(
        "--install",
        action="store_true",
        help="缺依赖时自动 pip install -r requirements.txt",
    )
    args = parser.parse_args()

    _check_deps(auto_install=args.install)

    import uvicorn

    from src.core.config import get_settings

    settings = get_settings()
    host = args.host or settings.app.host
    port = args.port or settings.app.port

    if args.reload:
        reload_enabled = True
    elif args.no_reload:
        reload_enabled = False
    else:
        reload_enabled = settings.app.env == "development"

    _banner(settings, host, port, reload_enabled)

    if args.open:
        shown_host = "localhost" if host in ("0.0.0.0", "127.0.0.1") else host
        Timer(1.5, lambda: webbrowser.open(f"http://{shown_host}:{port}/admin/")).start()

    # 用 import string 而不是 app 对象 —— 否则 reload 不生效
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        reload_dirs=[str(BACKEND_DIR / "src")] if reload_enabled else None,
        log_level="info" if settings.app.debug else "warning",
    )


if __name__ == "__main__":
    main()
