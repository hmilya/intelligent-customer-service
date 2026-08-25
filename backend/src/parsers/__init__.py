"""Document parsers registry.

Picks the right parser by file extension. Each parser turns the file into
plain UTF-8 text, which then gets chunked and embedded.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from .base import DocumentParseError, Parser
from .docx_parser import DocxParser
from .pdf_parser import PdfParser
from .txt_parser import TxtParser
from .xlsx_parser import XlsxParser

PARSERS: Dict[str, Parser] = {
    "txt":  TxtParser(),
    "docx": DocxParser(),
    "xlsx": XlsxParser(),
    "pdf":  PdfParser(),
}


def get_parser(filename: str) -> Parser:
    name = filename.lower()
    if name.endswith((".txt", ".md", ".markdown")):
        return PARSERS["txt"]
    if name.endswith(".docx"):
        return PARSERS["docx"]
    if name.endswith(".xlsx"):
        return PARSERS["xlsx"]
    if name.endswith(".pdf"):
        return PARSERS["pdf"]
    raise DocumentParseError(f"Unsupported file type: {filename}")


def get_parser_by_code(code: str) -> Parser:
    if code not in PARSERS:
        raise DocumentParseError(f"Unknown parser code: {code}")
    return PARSERS[code]
