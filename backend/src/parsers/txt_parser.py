"""Plain text parser."""
from __future__ import annotations

from pathlib import Path

from .base import DocumentParseError, Parser


class TxtParser(Parser):
    code = "txt"
    display_name = "纯文本 / Markdown"
    extensions = (".txt", ".md", ".markdown")

    def parse(self, path: str | Path) -> str:
        p = Path(path)
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                return p.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise DocumentParseError(f"Cannot decode text file: {p}")
