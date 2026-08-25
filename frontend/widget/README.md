# CustomerService Widget

A zero-dependency, embeddable chat widget for the Intelligent Customer
Service backend.

## Quick start

```html
<script src="/path/to/customer-service.js"></script>
<script>
  CustomerService.init({
    apiUrl: 'https://your-api.example.com',
    title: '智能客服小助手',
    accent: '#0a66c2',
    position: 'right',      // 'left' | 'right'
    enableUpload: true,
  });
</script>
```

## Init options

| Option         | Type                | Default                          | Description |
|----------------|---------------------|----------------------------------|-------------|
| `apiUrl`       | string              | `http://localhost:8000`          | Backend base URL |
| `title`        | string              | `智能客服`                       | Header title |
| `subtitle`     | string              | `在线`                           | Subtitle |
| `welcome`      | string              | `您好，请问有什么可以帮您？`      | First assistant message |
| `placeholder`  | string              | `输入您的问题…`                  | Input placeholder |
| `accent`       | string              | `#0a66c2`                        | Theme accent color |
| `position`     | `'left' \| 'right'` | `right`                          | Float-button corner |
| `autoOpen`     | boolean             | `false`                          | Auto-open on load |
| `enableUpload` | boolean             | `true`                           | Show file-upload button |
| `sessionId`    | string \| null      | `null`                           | Resume a prior session |
| `onReady`      | function            | `null`                           | Called after init |

## Public API

```js
CustomerService.open();          // show panel
CustomerService.close();         // hide panel
CustomerService.toggle();        // toggle
CustomerService.sendMessage(t);  // programmatic send
CustomerService.destroy();       // remove widget
```

## File upload

The widget's file button POSTs to `/api/documents/upload` (multipart) and
then calls `/api/documents/process` to chunk + embed + index. Supported
extensions: `.txt`, `.docx`, `.xlsx`, `.pdf`. Server-side limit: 20 MB
(configurable in `.env`).

## SSE events

The widget consumes `POST /api/chat/stream` (SSE). Expected event types:
`meta` (first; carries `session_id`), `token` (incremental text),
`sources` (final), `done`, `error`.

## iframe mode

For full isolation (styles and scripts can't touch the host page), point an
iframe at the backend's `/embed` route:

```html
<iframe src="https://api.example.com/embed?api=https://api.example.com"
        style="position:fixed;right:20px;bottom:20px;width:400px;height:636px;
               border:0;background:transparent;"></iframe>
```

`src` must be the **`/embed` page**, not `customer-service.js` — pointing at
the script file just renders its source as text.

Size and background both matter:

- **`400 × 636`** is what the expanded panel needs (panel `360×540`
  + button clearance `76` + margin `20`). Smaller clips the panel.
- **`background: transparent`** — otherwise the area the widget doesn't
  occupy shows the iframe's own colour as a visible block.

Accepted query params: `api`, `title`, `accent`, `position`, `autoOpen`,
`upload`, `bg` (e.g. `bg=f4f6f9` to paint a backdrop).

## Cross-platform

- **Website**: paste the `<script>` snippet.
- **Mini-program (WeChat / Alipay)**: use the `web-view` component pointing
  to a hosted version of this widget. The page wrapper and API server
  must be on the same origin or CORS-configured.
- **Desktop app (Electron / Tauri)**: load the same script in a
  `BrowserView` / `Webview`.
