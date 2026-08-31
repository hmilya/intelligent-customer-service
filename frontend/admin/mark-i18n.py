#!/usr/bin/env python3
"""
One-shot markup pass: add data-i18n / data-i18n-html / data-i18n-attr to
frontend/admin/index.html.

Idempotent and re-runnable from a clean checkout, so the marking rules are
reviewable rather than being 300 hand edits.

Rules
-----
data-i18n        element whose content is pure text containing CJK
data-i18n-html   element whose content is ONE sentence broken up by *inline*
                 tags (<code>/<strong>/<a>/<em>/<b>). Deliberately never
                 applied to containers holding block tags (<pre>, <div>, <p>,
                 <ol>, <button>…): those hold code samples and JS-updated
                 <span id=...> placeholders that a translator must not have to
                 reproduce, and blob-replacing their innerHTML would be fragile.
                 Their inner leaves get marked individually instead.
data-i18n-attr   comma-separated list of attributes whose values contain CJK
"""
import re
import sys

CJK = re.compile(r'[一-鿿぀-ヿ]')
# Tags that make an element a *container*, not a translatable sentence.
# <br> is deliberately absent: a two-line hint joined by <br> is still one
# translatable unit, and the translator may need to move the break.
BLOCK = re.compile(r'<(?:pre|div|p|ol|ul|li|h[1-6]|button|select|input|'
                   r'textarea|table|tr|td|th|iframe|img|label|section)\b', re.I)
INLINE = re.compile(r'<(?:code|strong|a|em|b|br)\b', re.I)

TEXT_TAGS = ('h1|h2|h3|h4|p|li|label|div|span|button|option|td|th|strong|'
             'small|a|summary|code')
ATTR_NAMES = ('title', 'placeholder', 'alt', 'aria-label')


def main(path):
    src = open(path, encoding='utf-8').read()
    # Search for the page script *after* <body>: the <head> now loads
    # /shared/locale.js and i18n.js, and slicing at the first "<script" anywhere
    # would put those in `tail` and duplicate the whole document.
    b = src.index('<body')
    s = src.index('<script', b)
    head, body, tail = src[:b], src[b:s], src[s:]
    assert head + body + tail == src, 'split lost or duplicated content'
    n = {'text': 0, 'html': 0, 'attr': 0, 'span': 0}

    # ---- 1. wrap bare CJK text that sits next to sibling elements ----------
    # These are label-plus-badge patterns, not sentences: wrapping keeps the
    # sibling's id (JS toggles them) intact.
    body, c = re.subn(r'(<span class="icon"></span>)([^<>]+)(</div>)',
                      r'\1<span data-i18n>\2</span>\3', body)
    n['span'] += c
    body, c = re.subn(r'(<input type="checkbox"[^<>]*/>)\s*([^<>]*[一-鿿][^<>]*?)(\s*</label>)',
                      r'\1 <span data-i18n>\2</span>\3', body)
    n['span'] += c
    body, c = re.subn(r'(<span class="pay-tab-ico [a-z]+">[^<>]*</span>)\s*([^<>]*[一-鿿][^<>]*?)(\s*</button>)',
                      r'\1 <span data-i18n>\2</span>\3', body)
    n['span'] += c
    for old, new in (
        ('              模型名称 <span id="llmModelReq"',
         '              <span data-i18n>模型名称</span> <span id="llmModelReq"'),
        ('必须与 Embedding 模型输出一致<span id="vecDimStrict"',
         '<span data-i18n>必须与 Embedding 模型输出一致</span><span id="vecDimStrict"'),
        ('<span class="spinner"></span>正在获取模型列表…',
         '<span class="spinner"></span><span data-i18n>正在获取模型列表…</span>'),
    ):
        if old in body:
            body = body.replace(old, new)
            n['span'] += 1

    # ---- 2. inline-broken sentences → data-i18n-html -----------------------
    def mark_html(m):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        if 'data-i18n' in attrs:
            return m.group(0)
        if not INLINE.search(inner) or BLOCK.search(inner):
            return m.group(0)              # container, or no inline tag at all
        if not CJK.search(re.sub(r'<[^>]*>', '', inner)):
            return m.group(0)              # no bare CJK outside the inline tag
        n['html'] += 1
        return f'<{tag}{attrs} data-i18n-html>{inner}</{tag}>'

    # One re.sub per tag, leaf-most tags first. This ordering is load-bearing:
    # re.sub advances past a whole match even when the callback declines it, so
    # scanning <div> first would consume a card and never look at the <li>s
    # inside it.
    for tag in ('span', 'small', 'code', 'strong', 'li', 'label', 'p', 'div'):
        body = re.sub(rf'<({tag})((?:[^<>"]|"[^"]*")*?)>'
                      rf'((?:(?!</?{tag}[ >])[\s\S])*?)</{tag}>', mark_html, body)


    # ---- 3. pure-text elements → data-i18n --------------------------------
    # Nodes whose text is written by JS must never be marked: apply() would
    # overwrite the runtime value with a translation of the placeholder that
    # happened to be in the HTML. #langLabel always shows the current language
    # in its own script (简体中文 / 日本語 / …), which is not translatable text.
    JS_OWNED = ('langLabel', 'embedApiUrl', 'embedApiUrl2', 'apiUrlDisplay')

    def mark_text(m):
        tag, attrs, text = m.group(1), m.group(2), m.group(3)
        if 'data-i18n' in attrs or '<' in text or not CJK.search(text):
            return m.group(0)
        if any(f'id="{i}"' in attrs for i in JS_OWNED):
            return m.group(0)
        n['text'] += 1
        return f'<{tag}{attrs} data-i18n>{text}</{tag}>'

    body = re.sub(rf'<({TEXT_TAGS})([^<>]*)>([^<>]+)</\1>', mark_text, body)

    # A data-i18n-html msgid is the whole sentence *including* its inline tags,
    # so a nested data-i18n would translate the same words twice — and worse,
    # the inner pass would run first and poison the outer snapshot. Strip them.
    def strip_nested(m):
        inner = re.sub(r'\s+data-i18n(?![-\w])', '', m.group(3))
        return f'<{m.group(1)}{m.group(2)}>{inner}</{m.group(1)}>'

    for tag in ('li', 'p', 'div', 'span', 'small', 'label'):
        body = re.sub(rf'<({tag})((?:[^<>"]|"[^"]*")*?\bdata-i18n-html\b(?:[^<>"]|"[^"]*")*?)>'
                      rf'((?:(?!</?{tag}[ >])[\s\S])*?)</{tag}>', strip_nested, body)

    # ---- 4. attributes → data-i18n-attr -----------------------------------
    def mark_attrs(m):
        tag, attrs = m.group(1), m.group(2)
        if 'data-i18n-attr' in attrs:
            return m.group(0)
        want = [a for a in ATTR_NAMES
                if (v := re.search(a + r'="([^"]*)"', attrs)) and CJK.search(v.group(1))]
        if not want:
            return m.group(0)
        n['attr'] += len(want)
        selfclose = attrs.rstrip().endswith('/')
        clean = attrs.rstrip().rstrip('/').rstrip()
        marker = f' data-i18n-attr="{",".join(want)}"'
        return f'<{tag}{clean}{marker}{" /" if selfclose else ""}>'

    body = re.sub(r'<([a-z]+)((?:[^<>"]|"[^"]*")*?)>', mark_attrs, body)

    open(path, 'w', encoding='utf-8').write(head + body + tail)
    print(f"marked: {n['text']} text, {n['html']} html, {n['attr']} attrs, "
          f"{n['span']} wrapping spans")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'index.html')
