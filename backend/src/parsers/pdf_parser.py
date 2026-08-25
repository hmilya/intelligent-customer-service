"""Optional PDF parser using PyPDF2."""
from __future__ import annotations

from pathlib import Path

from .base import DocumentParseError, Parser


class PdfParser(Parser):
    code = "pdf"
    display_name = "PDF 文档"
    extensions = (".pdf",)

    def parse(self, path: str | Path) -> str:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise DocumentParseError("PyPDF2 is not installed") from e

        p = Path(path)
        try:
            reader = PdfReader(str(p))
        except Exception as e:
            raise DocumentParseError(f"Failed to open pdf {p}: {e}") from e

        chunks: list[str] = []
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                chunks.append(f"## Page {i + 1}\n{text.strip()}")
        return "\n\n".join(chunks)
