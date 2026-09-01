# Embedding Guide

The customer-service widget (`frontend/widget/customer-service.js`) is a
single, zero-dependency JS file designed to drop into any environment
that can run JavaScript and make `fetch` calls.

## 1. Website (most common)

```html
<script src="https://cdn.example.com/customer-service.js"></script>
<script>
  CustomerService.init({
    apiUrl: 'https://api.example.com',
    title: '智能客服小助手',
    accent: '#0a66c2',
    position: 'right',          // 'left' or 'right'
    // Off by default: /api/documents/* requires an admin token.
    enableUpload: false,
  });
</script>
```

Add this to your site's `<body>` (footer is fine). The widget attaches
itself to `document.body` and uses a high `z-index`, so it floats above
your content without any CSS work.

### Options

| Option         | Type                | Default                | Description |
|----------------|---------------------|------------------------|-------------|
| `apiUrl`       | string              | `http://localhost:8000`| Backend base URL |
| `title`        | string              | `智能客服`             | Header title |
| `subtitle`     | string              | `在线`                 | Subtitle |
| `welcome`      | string              | `您好，请问有什么可以帮您？` | First assistant message |
| `accent`       | string              | `#0a66c2`              | Theme color |
| `position`     | `'left'\|'right'`   | `right`                | Float button corner |
| `autoOpen`     | boolean             | `false`                | Auto-open on load |
| `enableUpload` | boolean             | `false`                | Show file upload button (see note below) |
| `sessionId`    | string \| null      | `null`                 | Resume an existing session |
| `lang`         | `'auto'\|'zh-CN'\|'zh-TW'\|'ja'\|'en'` | `auto`  | UI **and answer** language |
| `onReady`      | function            | `null`                 | Hook fired after init |
| `onLangChange` | function            | `null`                 | Hook fired after the visitor switches language |

### Visitor file upload

`enableUpload` ships **off**. The upload button posts to `/api/documents/upload`,
which now requires an admin token — a visitor pressing it would only ever see a
401. Knowledge-base ingestion is an operator task, done from the admin console.

Turn it back on only if you have put your own authenticated proxy in front of
the document endpoints and are prepared to have anonymous visitors write into
your knowledge base.

### Language

`lang: 'auto'` (the default) picks the language from the visitor's **timezone**
first — `Asia/Shanghai` → 简体中文, `Asia/Taipei`/`Asia/Hong_Kong`/`Asia/Macau`
→ 繁體中文, `Asia/Tokyo` → 日本語, anything else → English — falling back to
`navigator.languages` when the timezone says nothing useful.

No IP geolocation is involved, deliberately: on an intranet the client address
is a `10.x`/`192.168.x` that carries no region, and no online geo service is
reachable anyway. **Detection works fully offline.**

The visitor can switch language from the widget's header, and the choice is
remembered in `localStorage` (key `cs_lang`, shared with the admin console).
Whatever language is active is sent with every request, so the AI answers in
that language too — the knowledge base stays Chinese, only the reply changes.

## 2. iframe (full isolation)

Useful when the host page and the API are on different origins and you
don't want to enable CORS.

```html
<iframe src="https://api.example.com/embed?api=https://api.example.com"
        style="position:fixed;right:20px;bottom:20px;width:400px;height:636px;
               border:0;background:transparent;">
</iframe>
```

The backend already serves this page at `/embed` — nothing to build.

**Two things that go wrong here:**

| Mistake | Symptom |
|---|---|
| iframe smaller than `400 × 636` | The expanded panel gets clipped |
| No `background: transparent` | Unused area shows the iframe's own colour — looks like a white block |

The `636` comes from the widget's own CSS: panel `540` + button clearance `76`
+ margin `20`. Width is panel `360` + margin `20 × 2`.

Query parameters `/embed` accepts:

| Param | Default | Meaning |
|---|---|---|
| `api` | same origin | Backend base URL |
| `title` · `accent` · `position` | 后台配置 | Override the admin console's settings |
| `autoOpen` | `1` | `0` = start collapsed |
| `upload` | `1` | `0` = hide the file-upload button |
| `bg` | transparent | Paint a backdrop, e.g. `bg=f4f6f9` |
| `lang` | auto-detected | Force a language: `zh-CN` / `zh-TW` / `ja` / `en` |

## 3. WeChat mini-program (小程序)

WeChat mini-programs don't allow `<script>` injection, but they do have a
`<web-view>` component that can load a remote URL.

```xml
<!-- mini-program/page/index/index.wxml -->
<web-view src="https://chat.example.com/?api=https://api.example.com" />
```

Host a tiny page (e.g. `chat.example.com/index.html`) that:

1. Reads the `api` query param.
2. Loads `customer-service.js`.
3. Calls `CustomerService.init({ apiUrl: api, autoOpen: true })`.

Add the chat domain to the mini-program's **业务域名** whitelist.

## 4. Alipay / Douyin / Baidu mini-programs

Same `<web-view>` pattern. Each platform has its own domain whitelist —
add the chat URL to the respective console.

## 5. Electron / Tauri desktop apps

### Electron

```js
// main.ts
const win = new BrowserWindow({ width: 1280, height: 800 });
await win.loadURL('https://chat.example.com/?api=https://api.example.com');
```

Or inject the widget directly into an existing renderer:

```js
await win.webContents.executeJavaScript(`
  (async () => {
    const s = document.createElement('script');
    s.src = 'https://cdn.example.com/customer-service.js';
    document.head.appendChild(s);
    await new Promise(r => s.onload = r);
    window.CustomerService.init({ apiUrl: 'https://api.example.com' });
  })();
`);
```

### Tauri

```rust
tauri::Builder::default()
    .setup(|app| {
        let window = tauri::WebviewWindowBuilder::new(
            app, "chat", tauri::WebviewUrl::External("https://chat.example.com/".parse().unwrap())
        ).build()?;
        Ok(())
    })
```

## 6. Native mobile (iOS / Android)

For full SDK-style integration, build a `WKWebView` (iOS) or
`WebView` (Android) that loads the same `chat.example.com` page.

## 7. SSR / server-rendered pages

If your site is server-rendered (Rails, Django, etc.), the widget works
identically — just include the `<script>` tag in your layout.

## CSP (Content Security Policy)

If your site uses CSP, allow:

```http
Content-Security-Policy:
  default-src 'self';
  script-src 'self' https://cdn.example.com;
  connect-src 'self' https://api.example.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
```

The widget injects a small `<style>` block; `'unsafe-inline'` for
`style-src` is required unless you self-host the CSS.

## Disabling the widget on certain pages

```js
if (window.location.pathname.startsWith('/admin')) {
  // Don't load on admin pages
} else {
  // normal embed
}
```
