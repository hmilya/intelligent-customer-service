"""The landing page at ``/`` is translated in the browser, not on the server.

Nothing in the app imports its markup, so a translator who adds a card and
forgets the catalog would only find out by loading the page in Japanese. These
tests read ``main.py`` as text and check the two halves agree.

The msgid is the Chinese source text itself (same convention as
``frontend/admin/i18n.js``), so a missing entry degrades to Chinese rather than
to a raw key -- which is exactly why it needs a test to be noticed at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MAIN_PY = Path(__file__).resolve().parents[1] / "main.py"
SOURCE = MAIN_PY.read_text(encoding="utf-8")

# The catalogs live in this constant; the marked-up HTML lives in root() below
# it. Splitting there keeps a catalog *key* from being mistaken for markup.
_SPLIT = "@asynccontextmanager"
SCRIPT, MARKUP = SOURCE.split(_SPLIT, 1)

LANGUAGES = ("zh-TW", "ja", "en")


def _msgids(attr: str) -> list[str]:
    """Chinese source strings marked with ``attr`` in the landing HTML."""
    # Text nodes: <h3 data-i18n>🚀 快速开始</h3>. Whitespace is collapsed to
    # match the norm() the browser applies before looking a msgid up.
    found = re.findall(rf"<(\w+)[^<>]*\b{attr}\b[^<>]*>(.*?)</\1>", MARKUP, re.S)
    return [re.sub(r"\s+", " ", text).strip() for _tag, text in found]


def test_landing_page_has_markup() -> None:
    """Guard the regexes themselves: if they stop matching, so do the tests."""
    assert len(_msgids("data-i18n(?![-\\w])")) >= 6
    assert len(_msgids("data-i18n-html")) >= 8


@pytest.mark.parametrize("attr", ["data-i18n(?![-\\w])", "data-i18n-html"])
def test_every_msgid_is_translated_into_every_language(attr: str) -> None:
    missing: list[str] = []
    for msgid in _msgids(attr):
        # Keys are single-quoted in the JS, and no msgid or translation contains
        # an apostrophe, so a literal count is unambiguous.
        assert "'" not in msgid, f"apostrophe in msgid breaks the check: {msgid}"
        hits = SCRIPT.count(f"'{msgid}':")
        if hits != len(LANGUAGES):
            missing.append(f"{msgid!r}: in {hits} of {len(LANGUAGES)} catalogs")
    assert not missing, "untranslated landing-page strings:\n" + "\n".join(missing)


def test_translations_keep_the_inline_tags() -> None:
    """A dropped <a> or <code> in a translation silently kills a link."""
    for msgid in _msgids("data-i18n-html"):
        tags = sorted(set(re.findall(r"<(\w+)", msgid)))
        if not tags:
            continue
        # Grab each catalog's value for this msgid: everything up to the next
        # key line or the end of that catalog object.
        for value in re.findall(
            rf"'{re.escape(msgid)}':\s*\n?\s*'(.*?)'(?=[,\n}}])", SCRIPT, re.S
        ):
            for tag in tags:
                assert f"<{tag}" in value, (
                    f"translation of {msgid!r} lost its <{tag}>: {value!r}"
                )


def test_source_language_has_no_catalog() -> None:
    """zh-CN must fall through to the msgid, not duplicate it."""
    assert "'zh-CN': {" not in SCRIPT


def test_html_lang_is_declared() -> None:
    """Screen readers and CJK font selection need it before JS runs."""
    assert '<html lang="zh-CN">' in MARKUP


def test_landing_page_loads_the_shared_detector() -> None:
    """Region detection must be the same code the widget and admin use."""
    assert '<script src="/shared/locale.js"></script>' in SCRIPT
