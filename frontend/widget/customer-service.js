/*!
 * CustomerService — embeddable chat widget (no build step required).
 * Usage:
 *   <script src="/path/customer-service.js"></script>
 *   <script>CustomerService.init({ apiUrl: 'https://api.example.com' });</script>
 *
 * Public API on window.CustomerService:
 *   init({ apiUrl, configId, title, subtitle, accent, position, autoOpen, sessionId, onReady })
 *   open() / close() / toggle()
 *   sendMessage(text)
 *   destroy()
 */
(function () {
  'use strict';

  // -------------------------------------------------------------------------
  // Config + state
  // -------------------------------------------------------------------------
  const DEFAULTS = {
    apiUrl: 'http://localhost:8000',
    configId: '',
    title: '智能客服',
    avatar: '',                 // image URL; falls back to the title's initial
    subtitle: '在线',
    welcome: '您好，请问有什么可以帮您？',
    placeholder: '输入您的问题…',
    accent: '#0a66c2',
    position: 'right',          // 'left' | 'right'
    autoOpen: false,
    sessionId: null,
    enableUpload: true,
    uploadHint: '支持 .txt / .md / .docx / .xlsx / .pdf，单文件 ≤ 20MB',
    // Pull 客服名称 / 头像 / 欢迎语 / 联系方式 from GET /api/config so the
    // admin console is the single source of truth. Anything passed to init()
    // explicitly still wins.
    useServerConfig: true,
    onReady: null,
  };

  let cfg = Object.assign({}, DEFAULTS);
  let sessionId = null;
  let isOpen = false;
  let rootEl = null;
  let messagesEl = null;
  let inputEl = null;
  let buttonEl = null;
  let panelEl = null;
  let fileBtnEl = null;
  let fileInputEl = null;
  let abortController = null;

  // -------------------------------------------------------------------------
  // Styles (injected once)
  // -------------------------------------------------------------------------
  const CSS = `
  .cs-root { all: initial; position: fixed; z-index: 2147483600; font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', Roboto, sans-serif; color: #222; }
  .cs-root * { box-sizing: border-box; }
  .cs-btn { width: 56px; height: 56px; border-radius: 50%; background: var(--cs-accent, #0a66c2); color: #fff; border: 0; cursor: pointer; box-shadow: 0 6px 18px rgba(0,0,0,.18); display: flex; align-items: center; justify-content: center; transition: transform .15s ease, box-shadow .15s ease; }
  .cs-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(0,0,0,.22); }
  .cs-btn svg { width: 26px; height: 26px; }
  .cs-pos-right { right: 20px; bottom: 20px; }
  .cs-pos-left  { left: 20px;  bottom: 20px; }
  .cs-panel { position: absolute; bottom: 76px; width: 360px; max-width: calc(100vw - 32px); height: 540px; max-height: calc(100vh - 120px); background: #fff; border-radius: 12px; box-shadow: 0 16px 48px rgba(0,0,0,.18); display: none; flex-direction: column; overflow: hidden; }
  .cs-pos-right .cs-panel { right: 0; }
  .cs-pos-left  .cs-panel { left: 0; }
  .cs-panel.open { display: flex; animation: cs-pop .18s ease-out; }
  @keyframes cs-pop { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  .cs-header { display: flex; align-items: center; gap: 10px; padding: 12px 14px; background: var(--cs-accent, #0a66c2); color: #fff; }
  .cs-header .avatar { width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,.2); display: flex; align-items: center; justify-content: center; font-weight: 600; overflow: hidden; flex-shrink: 0; }
  .cs-header .avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .cs-input .cs-upload svg { display: block; }
  .cs-header .meta { flex: 1; min-width: 0; }
  .cs-header .title { font-weight: 600; font-size: 14px; line-height: 1.2; }
  .cs-header .subtitle { font-size: 12px; opacity: .85; }
  .cs-header .close { background: transparent; border: 0; color: #fff; cursor: pointer; font-size: 22px; line-height: 1; padding: 4px; }
  .cs-messages { flex: 1; overflow-y: auto; padding: 12px; background: #f7f8fa; }
  .cs-msg { margin: 6px 0; display: flex; }
  .cs-msg.user { justify-content: flex-end; }
  /* pre-wrap keeps newlines visible while raw text streams in; once the
     Markdown is rendered into real elements it would add phantom blank
     lines, so the md class turns it off. */
  .cs-msg .bubble { max-width: 78%; padding: 8px 12px; border-radius: 12px; line-height: 1.5; font-size: 14px; word-wrap: break-word; white-space: pre-wrap; }
  .cs-msg .bubble.md { white-space: normal; }
  .cs-msg .bubble.md p, .cs-msg .bubble.md li { white-space: pre-wrap; }
  .cs-msg.user .bubble { background: var(--cs-accent, #0a66c2); color: #fff; border-bottom-right-radius: 2px; }
  .cs-msg.assistant .bubble { background: #fff; color: #222; border: 1px solid #eef0f3; border-bottom-left-radius: 2px; }
  .cs-msg .bubble a.cs-link { color: var(--cs-accent, #0a66c2); text-decoration: underline; word-break: break-all; }
  .cs-msg .bubble a.cs-link:hover { text-decoration: none; opacity: .8; }
  .cs-msg.user .bubble a.cs-link { color: #fff; }
  /* Rendered Markdown inside a chat bubble — compact, no huge headings. */
  .cs-msg .bubble p { margin: 0 0 8px; }
  .cs-msg .bubble p:last-child { margin-bottom: 0; }
  .cs-msg .bubble .cs-md-h { font-weight: 600; margin: 10px 0 6px; line-height: 1.35; }
  .cs-msg .bubble .cs-md-h:first-child { margin-top: 0; }
  .cs-msg .bubble .cs-md-h1 { font-size: 16px; }
  .cs-msg .bubble .cs-md-h2 { font-size: 15px; }
  .cs-msg .bubble .cs-md-h3 { font-size: 14px; }
  .cs-msg .bubble .cs-md-h4 { font-size: 13px; color: #4b5563; }
  .cs-msg .bubble ul, .cs-msg .bubble ol { margin: 4px 0 8px; padding-left: 20px; }
  .cs-msg .bubble li { margin: 3px 0; }
  .cs-msg .bubble li:last-child { margin-bottom: 0; }
  .cs-msg .bubble strong { font-weight: 600; }
  .cs-msg .bubble code { background: #f1f3f5; color: #c7254e; padding: 1px 5px; border-radius: 3px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; }
  .cs-msg .bubble pre { background: #1f2937; color: #e5e7eb; padding: 10px 12px; border-radius: 6px; overflow-x: auto; margin: 6px 0 8px; }
  .cs-msg .bubble pre code { background: none; color: inherit; padding: 0; font-size: 12px; line-height: 1.5; }
  .cs-msg .bubble blockquote { margin: 6px 0; padding: 4px 10px; border-left: 3px solid #d1d5db; color: #4b5563; background: #f9fafb; white-space: pre-wrap; }
  .cs-msg .bubble hr { border: 0; border-top: 1px solid #e5e7eb; margin: 10px 0; }
  .cs-msg.user .bubble code { background: rgba(255,255,255,.22); color: #fff; }
  .cs-msg.system .bubble { background: #fff7e6; color: #663c00; border: 1px solid #ffe7ba; font-size: 12px; }
  .cs-sources { margin-top: 6px; font-size: 12px; color: #666; }
  .cs-sources details { background: #f0f2f5; border-radius: 6px; padding: 4px 8px; }
  .cs-sources summary { cursor: pointer; }
  .cs-sources ol { padding-left: 20px; margin: 4px 0 0; }
  .cs-typing { display: inline-block; }
  .cs-typing span { display: inline-block; width: 4px; height: 4px; margin: 0 1px; background: #999; border-radius: 50%; animation: cs-dot 1.2s infinite ease-in-out; }
  .cs-typing span:nth-child(2) { animation-delay: .15s; }
  .cs-typing span:nth-child(3) { animation-delay: .3s; }
  @keyframes cs-dot { 0%, 80%, 100% { transform: scale(.6); opacity: .4; } 40% { transform: scale(1); opacity: 1; } }
  .cs-input { border-top: 1px solid #eef0f3; padding: 8px; background: #fff; display: flex; gap: 6px; align-items: flex-end; }
  .cs-input textarea { flex: 1; min-height: 36px; max-height: 120px; padding: 8px 10px; border: 1px solid #e0e3e8; border-radius: 8px; resize: none; font: inherit; font-size: 14px; outline: none; }
  .cs-input textarea:focus { border-color: var(--cs-accent, #0a66c2); }
  .cs-input button { border: 0; background: var(--cs-accent, #0a66c2); color: #fff; width: 40px; height: 40px; border-radius: 8px; cursor: pointer; font-size: 18px; }
  .cs-input button:disabled { opacity: .5; cursor: not-allowed; }
  .cs-input .cs-upload { background: #f0f2f5; color: #555; }
  .cs-upload-hint { font-size: 11px; color: #999; padding: 0 12px 8px; background: #fff; }
  .cs-error { color: #c0392b; font-size: 12px; margin: 4px 12px; }
  `;

  function injectStyles() {
    if (document.getElementById('cs-styles')) return;
    const s = document.createElement('style');
    s.id = 'cs-styles';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // -------------------------------------------------------------------------
  // DOM helpers
  // -------------------------------------------------------------------------
  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === 'class') node.className = attrs[k];
      else if (k === 'style') node.setAttribute('style', attrs[k]);
      else if (k === 'html') node.innerHTML = attrs[k];
      else if (k.startsWith('on') && typeof attrs[k] === 'function') node.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== undefined && attrs[k] !== null) node.setAttribute(k, attrs[k]);
    }
    if (children) {
      (Array.isArray(children) ? children : [children]).forEach(c => {
        if (c == null) return;
        node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
      });
    }
    return node;
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // -------------------------------------------------------------------------
  // API client
  // -------------------------------------------------------------------------
  function baseHeaders() {
    return { 'Content-Type': 'application/json' };
  }

  async function api(path, opts) {
    const url = cfg.apiUrl.replace(/\/+$/, '') + path;
    const init = Object.assign({ method: 'GET', headers: baseHeaders() }, opts || {});
    if (init.body && typeof init.body !== 'string') init.body = JSON.stringify(init.body);
    const r = await fetch(url, init);
    if (!r.ok) {
      const text = await r.text();
      let detail = text;
      try { detail = JSON.parse(text).error?.message || text; } catch (_) {}
      throw new Error(detail || ('HTTP ' + r.status));
    }
    const ct = r.headers.get('content-type') || '';
    if (ct.includes('application/json')) return r.json();
    return r.text();
  }

  // SSE consumer over fetch + ReadableStream (works in all modern browsers and
  // supports POST with body, unlike EventSource).
  async function ssePost(path, body, onEvent) {
    if (abortController) abortController.abort();
    abortController = new AbortController();
    const url = cfg.apiUrl.replace(/\/+$/, '') + path;
    const r = await fetch(url, {
      method: 'POST',
      headers: baseHeaders(),
      body: JSON.stringify(body),
      signal: abortController.signal,
    });
    if (!r.ok) {
      const text = await r.text();
      let detail = text;
      try { detail = JSON.parse(text).error?.message || text; } catch (_) {}
      throw new Error(detail || ('HTTP ' + r.status));
    }
    const reader = r.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const ev = parseSSEBlock(raw);
        if (ev) onEvent(ev);
      }
    }
    // tail
    if (buffer.trim()) {
      const ev = parseSSEBlock(buffer);
      if (ev) onEvent(ev);
    }
  }

  function parseSSEBlock(block) {
    let event = 'message';
    const dataLines = [];
    for (const line of block.split('\n')) {
      if (!line) continue;
      if (line.startsWith(':')) continue;       // comment
      const i = line.indexOf(':');
      const field = i === -1 ? line : line.slice(0, i);
      let value = i === -1 ? '' : line.slice(i + 1);
      if (value.startsWith(' ')) value = value.slice(1);
      if (field === 'event') event = value;
      else if (field === 'data') dataLines.push(value);
    }
    if (!dataLines.length && event === 'message') return null;
    const dataStr = dataLines.join('\n');
    let data;
    try { data = JSON.parse(dataStr); } catch (_) { data = dataStr; }
    return { event, data };
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  function ensureRoot() {
    if (rootEl) return rootEl;
    injectStyles();
    rootEl = el('div', {
      class: 'cs-root ' + (cfg.position === 'left' ? 'cs-pos-left' : 'cs-pos-right'),
      style: '--cs-accent: ' + cfg.accent,
    });

    buttonEl = el('button', {
      class: 'cs-btn',
      'aria-label': '打开客服',
      onclick: toggle,
      html: chatBubbleIcon(),
    });

    panelEl = el('div', { class: 'cs-panel' });
    panelEl.appendChild(buildHeader());
    messagesEl = el('div', { class: 'cs-messages' });
    panelEl.appendChild(messagesEl);
    if (cfg.enableUpload) {
      panelEl.appendChild(buildUploadHint());
    }
    panelEl.appendChild(buildInput());

    rootEl.appendChild(buttonEl);
    rootEl.appendChild(panelEl);
    document.body.appendChild(rootEl);
    return rootEl;
  }

  function buildHeader() {
    return el('div', { class: 'cs-header' }, [
      buildAvatar(),
      el('div', { class: 'meta' }, [
        el('div', { class: 'title', id: 'cs-title' }, cfg.title),
        el('div', { class: 'subtitle', id: 'cs-subtitle' }, cfg.subtitle),
      ]),
      el('button', { class: 'close', 'aria-label': '关闭', onclick: close }, '×'),
    ]);
  }

  /** Avatar: an <img> when a URL is configured, otherwise the title's initial. */
  function buildAvatar() {
    const wrap = el('div', { class: 'avatar' });
    const url = (cfg.avatar || '').trim();
    if (url) {
      const img = el('img', { src: url, alt: cfg.title || '客服' });
      // Fall back to the initial if the image 404s or is blocked.
      img.addEventListener('error', () => {
        wrap.innerHTML = '';
        wrap.textContent = (cfg.title || '客').slice(0, 1);
      });
      wrap.appendChild(img);
    } else {
      wrap.textContent = (cfg.title || '客').slice(0, 1);
    }
    return wrap;
  }

  function buildInput() {
    const wrap = el('div', { class: 'cs-input' });
    if (cfg.enableUpload) {
      fileBtnEl = el('button', {
        class: 'cs-upload', title: '上传文件', onclick: pickFile,
        // `html` (not children) — a string child becomes a text node, which
        // would print the SVG source instead of rendering it.
        html: paperclipIcon(),
      });
      fileInputEl = el('input', { type: 'file', accept: '.txt,.md,.markdown,.docx,.xlsx,.pdf', style: 'display:none', onchange: handleFileChosen });
      wrap.appendChild(fileBtnEl);
      wrap.appendChild(fileInputEl);
    }
    inputEl = el('textarea', { rows: '1', placeholder: cfg.placeholder, onkeydown: handleKey });
    wrap.appendChild(inputEl);
    wrap.appendChild(el('button', { class: 'cs-send', title: '发送', onclick: () => sendCurrent() }, '➤'));
    return wrap;
  }

  function buildUploadHint() {
    return el('div', { class: 'cs-upload-hint' }, cfg.uploadHint);
  }

  function appendMessage(role, text, sources) {
    if (!messagesEl) return null;
    const wrap = el('div', { class: 'cs-msg ' + role });
    const bubble = el('div', { class: 'bubble' });
    bubble.textContent = text;
    wrap.appendChild(bubble);
    if (sources && sources.length) {
      const det = el('details');
      const sum = el('summary', null, `引用 ${sources.length} 条资料`);
      const ol = el('ol');
      sources.forEach(s => {
        const li = el('li');
        const head = s.filename ? `[${s.score || 0}] ${s.filename}` : `[${s.score || 0}] ${s.chunk_id}`;
        li.appendChild(document.createTextNode(head + ' — '));
        const code = el('span');
        code.textContent = (s.text || '').slice(0, 120) + (s.text && s.text.length > 120 ? '…' : '');
        li.appendChild(code);
        ol.appendChild(li);
      });
      det.appendChild(sum);
      det.appendChild(ol);
      const src = el('div', { class: 'cs-sources' });
      src.appendChild(det);
      wrap.appendChild(src);
    }
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return { wrap, bubble };
  }

  function appendTyping(role) {
    const { wrap, bubble } = appendMessage(role, '');
    bubble.innerHTML = '<span class="cs-typing"><span></span><span></span><span></span></span>';
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return { wrap, bubble };
  }

  function chatBubbleIcon() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
  }
  function paperclipIcon() {
    return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>';
  }

  // -------------------------------------------------------------------------
  // Behavior
  // -------------------------------------------------------------------------
  function open() {
    ensureRoot();
    panelEl.classList.add('open');
    isOpen = true;
    if (inputEl) inputEl.focus();
  }
  function close() {
    if (!panelEl) return;
    panelEl.classList.remove('open');
    isOpen = false;
  }
  function toggle() { isOpen ? close() : open(); }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendCurrent();
    }
  }

  function sendCurrent() {
    const text = (inputEl.value || '').trim();
    if (!text) return;
    inputEl.value = '';
    sendMessage(text);
  }

  /**
   * Render the finished answer: strip citation markers, then convert the
   * Markdown the model emits into real HTML.
   *
   * Streaming appends to textContent (XSS-safe, no reflow per token), so the
   * bubble holds raw Markdown until this runs. Everything is built with
   * createElement/textContent rather than innerHTML on model output, so a
   * malicious document in the knowledge base can't inject script.
   */
  function renderAnswer(bubble) {
    if (!bubble || bubble.dataset.rendered === '1') return;
    const raw = bubble.textContent || '';
    if (!raw.trim()) return;
    bubble.dataset.rendered = '1';

    // --- 1. Drop citation markers like [1], [2][3], 【1】 ---------------
    // `arr[0]` (code) and `2587.html[1]` (citation) are genuinely ambiguous.
    // We optimise for citations, which appear on most answers, over array
    // indexing, which is rare in customer-service replies.
    const text = raw
      .replace(/(?:[[［【]\s*\d+\s*[\]］】])+(?=\s|$|[，。；、！？）)])/g, '')
      .replace(/(?<=[一-鿿”"』」）)])(?:[[［【]\s*\d+\s*[\]］】])+/g, '')
      .replace(/[ \t]+([，。；、！？\n])/g, '$1')
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    bubble.innerHTML = '';
    bubble.classList.add('md');
    renderMarkdown(bubble, text);
  }

  /** Inline formatting: **bold**, *italic*, `code`, links, bare URLs. */
  function renderInline(target, text) {
    // Bare-URL matching uses an ALLOW-list of RFC 3986 characters rather than
    // "anything but whitespace". A deny-list let CJK text run into the link:
    // ".../kecheng，免费分享课程" was swallowed whole because the Chinese comma
    // and the following characters weren't excluded. The trailing class also
    // drops sentence-final punctuation so "见 https://x.com/a.html。" keeps 。
    // outside the anchor.
    const URL_RE = "https?://[A-Za-z0-9\\-._~:/?#\\[\\]@!$&'()*+,;=%]*[A-Za-z0-9\\-_~/#@$&*+=%]";

    // Ordered by precedence; each alternative captures its own payload.
    const re = new RegExp([
      '`([^`]+)`',                                  // 1 code
      '\\*\\*([^*]+)\\*\\*',                        // 2 bold
      '__([^_]+)__',                                // 3 bold
      '(?<![\\w*])\\*([^*\\n]+)\\*(?![\\w*])',      // 4 italic
      '\\[([^\\]]+)\\]\\((https?://[^\\s)]+)\\)',   // 5,6 [text](url)
      `(${URL_RE})`,                                // 7 bare url
    ].join('|'), 'g');

    let last = 0;
    let m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) {
        target.appendChild(document.createTextNode(text.slice(last, m.index)));
      }
      if (m[1] !== undefined) {
        const c = document.createElement('code');
        c.textContent = m[1];
        target.appendChild(c);
      } else if (m[2] !== undefined || m[3] !== undefined) {
        const b = document.createElement('strong');
        b.textContent = m[2] !== undefined ? m[2] : m[3];
        target.appendChild(b);
      } else if (m[4] !== undefined) {
        const i = document.createElement('em');
        i.textContent = m[4];
        target.appendChild(i);
      } else if (m[5] !== undefined && m[6] !== undefined) {
        target.appendChild(makeLink(m[6], m[5]));
      } else if (m[7] !== undefined) {
        target.appendChild(makeLink(m[7], m[7]));
      }
      last = m.index + m[0].length;
    }
    if (last < text.length) {
      target.appendChild(document.createTextNode(text.slice(last)));
    }
  }

  function makeLink(href, label) {
    const a = document.createElement('a');
    a.href = href;
    a.textContent = label;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.className = 'cs-link';
    return a;
  }

  /**
   * Block-level Markdown: headings, bullet/numbered lists, fenced code,
   * blockquotes, paragraphs. Deliberately small — just what an LLM answer
   * actually uses. No external dependency.
   */
  function renderMarkdown(root, text) {
    const lines = text.split('\n');
    let i = 0;
    let list = null;          // current <ul>/<ol> being filled

    const closeList = () => { list = null; };

    while (i < lines.length) {
      const line = lines[i];

      // Fenced code block
      const fence = line.match(/^\s*```\s*(\S*)\s*$/);
      if (fence) {
        closeList();
        const body = [];
        i++;
        while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) {
          body.push(lines[i]);
          i++;
        }
        i++;  // skip closing fence
        const pre = document.createElement('pre');
        const code = document.createElement('code');
        code.textContent = body.join('\n');
        pre.appendChild(code);
        root.appendChild(pre);
        continue;
      }

      // Heading: #..###### — rendered at a size that fits a chat bubble.
      const h = line.match(/^\s*(#{1,6})\s+(.*)$/);
      if (h) {
        closeList();
        const el = document.createElement('div');
        el.className = 'cs-md-h cs-md-h' + Math.min(h[1].length, 4);
        renderInline(el, h[2].trim());
        root.appendChild(el);
        i++;
        continue;
      }

      // Blockquote
      const q = line.match(/^\s*>\s?(.*)$/);
      if (q) {
        closeList();
        const bq = document.createElement('blockquote');
        const parts = [q[1]];
        i++;
        while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
          parts.push(lines[i].replace(/^\s*>\s?/, ''));
          i++;
        }
        renderInline(bq, parts.join('\n'));
        root.appendChild(bq);
        continue;
      }

      // Horizontal rule
      if (/^\s*([-*_])\s*\1\s*\1[\s\S]*$/.test(line) && !/[^\s\-*_]/.test(line)) {
        closeList();
        root.appendChild(document.createElement('hr'));
        i++;
        continue;
      }

      // List item: -, *, • or 1. / 1)
      const li = line.match(/^(\s*)(?:[-*•]|(\d+)[.)])\s+(.*)$/);
      if (li) {
        const ordered = li[2] !== undefined;
        const wantTag = ordered ? 'OL' : 'UL';
        if (!list || list.tagName !== wantTag) {
          list = document.createElement(ordered ? 'ol' : 'ul');
          root.appendChild(list);
        }
        const item = document.createElement('li');
        // Continuation lines (indented, not a new item) belong to this item —
        // the model often puts a URL on its own indented line.
        const buf = [li[3]];
        i++;
        while (i < lines.length
               && /^\s{2,}\S/.test(lines[i])
               && !/^(\s*)(?:[-*•]|\d+[.)])\s+/.test(lines[i])) {
          buf.push(lines[i].trim());
          i++;
        }
        renderInline(item, buf.join('\n'));
        list.appendChild(item);
        continue;
      }

      // Blank line ends a list / paragraph
      if (!line.trim()) {
        closeList();
        i++;
        continue;
      }

      // Paragraph: gather until a blank line or a block-level marker
      closeList();
      const para = [line];
      i++;
      while (i < lines.length
             && lines[i].trim()
             && !/^\s*(#{1,6}\s|>|```|[-*•]\s|\d+[.)]\s)/.test(lines[i])) {
        para.push(lines[i]);
        i++;
      }
      const p = document.createElement('p');
      renderInline(p, para.join('\n'));
      root.appendChild(p);
    }
  }

  async function sendMessage(text) {
    ensureRoot();
    if (!isOpen) open();
    appendMessage('user', text);
    const placeholder = appendTyping('assistant');
    try {
      await ssePost('/api/chat/stream', { session_id: sessionId, message: text }, (ev) => {
        if (ev.event === 'meta' && ev.data && ev.data.session_id) {
          sessionId = ev.data.session_id;
        } else if (ev.event === 'token' && ev.data && ev.data.text) {
          if (placeholder.bubble.querySelector('.cs-typing')) {
            placeholder.bubble.innerHTML = '';
            placeholder.bubble.textContent = '';
          }
          placeholder.bubble.textContent += ev.data.text;
          messagesEl.scrollTop = messagesEl.scrollHeight;
        } else if (ev.event === 'sources') {
          // Sources arrive right before `done`, so the answer text is complete.
          renderAnswer(placeholder.bubble);
        } else if (ev.event === 'error') {
          placeholder.bubble.innerHTML = '';
          placeholder.bubble.textContent = '⚠ ' + (ev.data?.message || '出错了');
        } else if (ev.event === 'done') {
          // Safety net: `sources` normally arrives first and triggers the
          // render, but it can be skipped (e.g. retrieval returned nothing).
          // renderAnswer() is idempotent, so calling it again is free.
          renderAnswer(placeholder.bubble);
          messagesEl.scrollTop = messagesEl.scrollHeight;
        }
      });
    } catch (e) {
      placeholder.bubble.innerHTML = '';
      placeholder.bubble.textContent = '⚠ ' + e.message;
    }
  }

  function pickFile() {
    if (fileInputEl) fileInputEl.click();
  }

  async function handleFileChosen(e) {
    const f = e.target.files && e.target.files[0];
    e.target.value = '';
    if (!f) return;
    ensureRoot();
    if (!isOpen) open();

    // appendMessage returns { wrap, bubble } — keep the bubble to update in place.
    const notice = appendMessage('system', `正在上传：${f.name}（${(f.size / 1024).toFixed(1)} KB）…`);
    const say = (text) => { if (notice && notice.bubble) notice.bubble.textContent = text; };
    const base = cfg.apiUrl.replace(/\/+$/, '');

    try {
      const fd = new FormData();
      fd.append('file', f);
      const r = await fetch(base + '/api/documents/upload', { method: 'POST', body: fd });
      const upText = await r.text();
      let up;
      try { up = upText ? JSON.parse(upText) : null; } catch (_) { up = null; }
      if (!r.ok) {
        throw new Error((up && up.error && up.error.message) || upText || ('HTTP ' + r.status));
      }

      say(`已上传 ${up.filename}，正在解析并入库…`);

      const pr = await fetch(base + '/api/documents/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: up.id }),
      });
      const pdText = await pr.text();
      let pd;
      try { pd = pdText ? JSON.parse(pdText) : null; } catch (_) { pd = null; }

      if (!pr.ok) {
        throw new Error((pd && pd.error && pd.error.message) || pdText || ('HTTP ' + pr.status));
      }
      // /process answers 200 even when ingestion failed — the outcome is in
      // `status`, so checking pr.ok alone would report a bogus success.
      if (pd && pd.status === 'ready') {
        say(`✅ ${up.filename} 已入库：${pd.chunk_count} 个片段，现在可以就它提问了`);
      } else {
        say(`⚠ ${up.filename} 入库失败：${(pd && pd.error_message) || '未知错误'}`);
      }
    } catch (err) {
      say('⚠ 上传失败：' + err.message);
    }
  }

  // -------------------------------------------------------------------------
  // Public init
  // -------------------------------------------------------------------------
  /**
   * Fetch 客服信息 from the backend and merge it in.
   *
   * Only fields the caller did NOT pass to init() get overwritten, so an
   * explicit `title` in the embed snippet still beats the admin console.
   */
  async function applyServerConfig(explicitKeys) {
    try {
      const c = await api('/api/config');
      if (!c) return;
      const fromServer = {
        title: c.name,
        avatar: c.avatar,
        welcome: c.welcome_message,
      };
      for (const k in fromServer) {
        const v = fromServer[k];
        if (v && !explicitKeys.has(k)) cfg[k] = v;
      }
      // Surface contact details in the subtitle when the admin filled them in.
      if (!explicitKeys.has('subtitle')) {
        const contact = [c.contact_phone, c.contact_email].filter(Boolean).join(' · ');
        if (contact) cfg.subtitle = contact;
      }
    } catch (_) {
      // Offline or CORS-blocked — keep the defaults, don't break the widget.
    }
  }

  /** Re-render the header + welcome line after config arrives. */
  function refreshHeader() {
    if (!panelEl) return;
    const old = panelEl.querySelector('.cs-header');
    if (old) panelEl.replaceChild(buildHeader(), old);
    // Replace the placeholder welcome text if it hasn't been talked over yet.
    if (messagesEl && messagesEl.children.length === 1 && cfg.welcome) {
      const bubble = messagesEl.querySelector('.cs-msg.assistant .bubble');
      if (bubble) bubble.textContent = cfg.welcome;
    }
  }

  function init(options) {
    const explicitKeys = new Set(Object.keys(options || {}));
    cfg = Object.assign({}, DEFAULTS, options || {});
    sessionId = cfg.sessionId || null;

    const start = async () => {
      ensureRoot();
      if (messagesEl && !messagesEl.children.length && cfg.welcome) {
        appendMessage('assistant', cfg.welcome);
      }
      if (cfg.autoOpen) open();

      if (cfg.useServerConfig) {
        await applyServerConfig(explicitKeys);
        refreshHeader();
      }

      if (typeof cfg.onReady === 'function') {
        try { cfg.onReady({ open, close, toggle, sendMessage }); } catch (_) {}
      }
    };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', start, { once: true });
    } else {
      start();
    }
  }

  function destroy() {
    if (rootEl && rootEl.parentNode) rootEl.parentNode.removeChild(rootEl);
    rootEl = panelEl = messagesEl = inputEl = buttonEl = fileBtnEl = fileInputEl = null;
    if (abortController) abortController.abort();
    abortController = null;
    isOpen = false;
  }

  // Expose
  window.CustomerService = { init, open, close, toggle, sendMessage, destroy };
})();
