#!/usr/bin/env python3
"""自动重试入库，直到全部片段完成。

为什么需要这个脚本
------------------
部分厂商（实测火山方舟 ARK）的 embedding 配额是长周期累计的：连续跑几百个
片段就会持续返回 429，等几十秒才恢复一点。手动点「入库」要点很多次。

本脚本利用 `process_document` 的**断点续传**能力：每轮从上次停下的片段继续，
已完成的不会重复消耗配额。遇到限流就休息一会儿再来，直到 status 变成 ready。

用法
----
    # 处理所有未完成的文档
    python scripts/ingest_retry.py

    # 只处理某个文档
    python scripts/ingest_retry.py --document-id abc123

    # 批量导入一个目录（先上传，再自动重试入库）
    python scripts/ingest_retry.py --dir ../docs/qqmu-knowledge-base

    # 调整节奏
    python scripts/ingest_retry.py --cooldown 90 --max-rounds 200

按 Ctrl+C 可随时中断，已完成的片段不会丢失，下次接着跑。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.config import get_settings  # noqa: E402
from src.core.database import dispose_engine  # noqa: E402
from src.services.document_service import DocumentService  # noqa: E402

SUPPORTED = {".txt", ".md", ".markdown", ".docx", ".xlsx", ".pdf"}


def fmt_secs(s: float) -> str:
    m, sec = divmod(int(s), 60)
    return f"{m}m{sec:02d}s" if m else f"{sec}s"


async def upload_dir(svc: DocumentService, directory: Path) -> list[str]:
    """上传目录下所有支持的文件，返回未完成的 document_id 列表。"""
    files = sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED)
    if not files:
        print(f"⚠ {directory} 下没有可上传的文件（支持 {', '.join(sorted(SUPPORTED))}）")
        return []

    print(f"发现 {len(files)} 个文件，开始上传…")
    ids: list[str] = []
    for fp in files:
        try:
            info = await svc.save_upload(fp.name, fp.read_bytes())
            status = info.get("status")
            mark = "已入库" if status == "ready" else "待入库"
            print(f"  [{mark}] {fp.name}  ({info['file_size'] / 1024:.0f} KB)")
            if status != "ready":
                ids.append(info["id"])
        except Exception as e:
            print(f"  [失败]   {fp.name}: {e}")
    return ids


async def pending_ids(svc: DocumentService) -> list[str]:
    docs = await svc.list_documents()
    return [d["id"] for d in docs if d["status"] != "ready"]


async def ingest_one(
    svc: DocumentService, doc_id: str, *, cooldown: float, max_rounds: int
) -> bool:
    """反复入库同一文档直到完成。返回是否成功。"""
    started = time.time()
    last_done = -1
    stalled = 0

    for rnd in range(1, max_rounds + 1):
        try:
            r = await svc.process_document(doc_id)
        except Exception as e:
            # DocumentError 里带着「已完成 N/M」，这是预期的中断
            r = None
            err = str(e)
        else:
            err = r.get("error_message") or ""

        # 读回真实进度
        docs = {d["id"]: d for d in await svc.list_documents()}
        d = docs.get(doc_id)
        if d is None:
            print(f"  文档已不存在（可能被删除）: {doc_id}")
            return False

        done, total = d.get("chunks_done") or 0, d.get("chunks_total") or 0
        name = d["filename"]
        pct = f"{done * 100 // total}%" if total else "--"

        if d["status"] == "ready":
            print(f"  ✅ {name} 完成：{d['chunk_count']} 片段，共用 {fmt_secs(time.time() - started)}")
            return True

        # 没有推进就多等一会儿 —— 说明配额还没回来
        if done == last_done:
            stalled += 1
        else:
            stalled = 0
        last_done = done

        wait = cooldown * min(4, 1 + stalled)
        reason = "配额未恢复" if stalled else "限流"
        print(
            f"  第 {rnd:>3} 轮 · {name} {done}/{total} ({pct}) · {reason}，"
            f"等 {fmt_secs(wait)} 后继续 …"
        )
        try:
            await asyncio.sleep(wait)
        except asyncio.CancelledError:
            raise

    print(f"  ⚠ 达到最大轮数 {max_rounds}，仍未完成。可再次运行本脚本继续。")
    return False


async def main() -> int:
    ap = argparse.ArgumentParser(description="自动重试入库直到完成")
    ap.add_argument("--document-id", help="只处理指定文档")
    ap.add_argument("--dir", type=Path, help="先上传该目录下的文件，再入库")
    ap.add_argument("--cooldown", type=float, default=60.0,
                    help="每轮之间的基础等待秒数（默认 60；无进展时自动加长）")
    ap.add_argument("--max-rounds", type=int, default=100,
                    help="单个文档最多重试多少轮（默认 100）")
    args = ap.parse_args()

    settings = get_settings()
    svc = DocumentService(settings)

    print("=" * 66)
    print("  自动重试入库")
    print("=" * 66)
    print(f"  向量模型 : {settings.embedding.model or '(读数据库配置)'}")
    print(f"  向量库   : {settings.vector_db.provider} / {settings.vector_db.collection}")
    print(f"  冷却时间 : {args.cooldown:.0f}s（无进展时自动延长到 4 倍）")
    print("=" * 66)
    print()

    if args.dir:
        await upload_dir(svc, args.dir)
        print()

    ids = [args.document_id] if args.document_id else await pending_ids(svc)
    if not ids:
        print("✅ 没有待入库的文档，全部已就绪。")
        await dispose_engine()
        return 0

    print(f"待入库 {len(ids)} 个文档\n")
    ok = 0
    t0 = time.time()
    try:
        for i, doc_id in enumerate(ids, 1):
            print(f"[{i}/{len(ids)}] {doc_id}")
            if await ingest_one(svc, doc_id, cooldown=args.cooldown, max_rounds=args.max_rounds):
                ok += 1
            print()
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\n已中断。进度已保存，再次运行本脚本会从中断处继续。")

    print("=" * 66)
    print(f"  完成 {ok}/{len(ids)} 个文档，总用时 {fmt_secs(time.time() - t0)}")
    print("=" * 66)
    await dispose_engine()
    return 0 if ok == len(ids) else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n已中断。")
        sys.exit(130)
