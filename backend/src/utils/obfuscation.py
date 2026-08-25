"""Light obfuscation helpers for storing API keys in DB / config files.

Matches the pattern in the user's Text2SQL_Assistant: base64 prefixing
so plaintext keys aren't sitting on disk. NOT encryption — use a real
KMS / secrets manager in production.
"""
from __future__ import annotations

import base64

_PREFIX = "b64:"


def obfuscate(text: str | None) -> str:
    if not text:
        return ""
    try:
        return _PREFIX + base64.b64encode(text.encode("utf-8")).decode("ascii")
    except Exception:
        return ""


def deobfuscate(text: str | None) -> str:
    if not text:
        return ""
    if text.startswith(_PREFIX):
        try:
            return base64.b64decode(text[len(_PREFIX):].encode("ascii")).decode("utf-8")
        except Exception:
            return ""
    return text
