#!/usr/bin/env node
/**
 * Widget 自检：在真实 DOM 里跑一遍完整 SSE 流程。
 *
 * 为什么需要这个：`node -c` 只做语法检查，检不出「模板字符串被内部反引号
 * 截断」这类错误 —— 那会让整个 IIFE 在运行时抛错、widget 完全不工作，但
 * 静态检查一片绿。这个脚本用假 SSE 驱动真实渲染路径，任何破坏都会暴露。
 *
 * 用法：node selftest.mjs   （需要 jsdom：npm i -D jsdom）
 */
import { JSDOM } from 'jsdom';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, 'customer-service.js'), 'utf8');

// Mirrors what the model actually produces, including the cases that have
// broken before: a URL followed by a Chinese comma + more text, a URL ending
// a sentence with 。, and trailing citation markers.
const ANSWER = `- **星空特效**：夜空背景动画，文章地址：https://www.qqmu.com/2497.html
- **流星雨**：用 \`canvas\` 实现，地址：https://www.qqmu.com/2569.html
- 编程课程栏目：https://www.qqmu.com/category/kecheng，免费分享一些编程相关的课程

### 更多
详见栏目：https://www.qqmu.com/category/texiao[1][2]
官网地址：https://www.qqmu.com/`;

function sseBody() {
  const out = [`event: meta\ndata: {"session_id":"s1"}\n\n`];
  for (const ch of ANSWER.match(/.{1,12}/gs)) {
    out.push(`event: token\ndata: ${JSON.stringify({ text: ch })}\n\n`);
  }
  out.push(`event: sources\ndata: [{"index":1,"chunk_id":"c1","text":"x","score":0.8}]\n\n`);
  out.push(`event: done\ndata: {"ok":true}\n\n`);
  return out.join('');
}

const dom = new JSDOM('<!DOCTYPE html><body></body>', {
  url: 'http://localhost/', runScripts: 'outside-only', pretendToBeVisual: true,
});
const { window } = dom;
// jsdom omits these globals; the widget's SSE reader and upload path need them.
window.TextDecoder = TextDecoder;
window.TextEncoder = TextEncoder;
window.AbortController = AbortController;
window.fetch = async (url) => {
  const u = String(url);
  if (u.includes('/api/chat/stream')) {
    const bytes = new TextEncoder().encode(sseBody());
    let sent = false;
    return { ok: true, status: 200, headers: { get: () => 'text/event-stream' },
      body: { getReader: () => ({ read: async () => (sent ? { done: true } : ((sent = true), { value: bytes, done: false })) }) } };
  }
  return { ok: false, status: 404, text: async () => '' };
};

// A broken template literal throws right here — that's the main thing we catch.
window.eval(src);
window.CustomerService.init({ apiUrl: 'http://x', useServerConfig: false, autoOpen: true });
await new Promise(r => setTimeout(r, 150));
window.CustomerService.sendMessage('星空特效');
await new Promise(r => setTimeout(r, 1200));

const d = window.document;
const bubble = [...d.querySelectorAll('.cs-msg.assistant .bubble')].pop();
const checks = [
  ['widget 初始化',       () => !!d.querySelector('.cs-root')],
  ['CSS 完整注入',        () => (d.getElementById('cs-styles')?.textContent || '').includes('cs-md-h')],
  ['回形针为 SVG',        () => !!d.querySelector('.cs-upload svg')],
  ['答案已渲染 (.md)',    () => bubble?.classList.contains('md')],
  ['链接转 <a>',          () => (bubble?.querySelectorAll('a.cs-link').length || 0) >= 3],
  ['href 有效',           () => bubble?.querySelector('a.cs-link')?.getAttribute('href')?.startsWith('http')],
  ['target=_blank',       () => bubble?.querySelector('a.cs-link')?.getAttribute('target') === '_blank'],
  ['**加粗** → strong',   () => !!bubble?.querySelector('strong')],
  ['`代码` → code',       () => !!bubble?.querySelector('code')],
  ['列表 → ul',           () => !!bubble?.querySelector('ul')],
  ['### → 标题',          () => !!bubble?.querySelector('.cs-md-h')],
  ['引用标记已清除',      () => !/\[\s*\d+\s*\]/.test(bubble?.textContent || '')],
  ['无旧引用面板',        () => !d.querySelector('.cs-sources')],
  // Regression: a deny-list URL pattern used to swallow the CJK text after a
  // link ("…/kecheng，免费分享…" became one giant anchor).
  ['链接不吞后续中文',    () => {
    const a = [...(bubble?.querySelectorAll('a.cs-link') || [])]
      .find(x => x.getAttribute('href')?.includes('/kecheng'));
    return a && a.getAttribute('href') === 'https://www.qqmu.com/category/kecheng';
  }],
  ['被吞的文字仍在气泡里', () => (bubble?.textContent || '').includes('免费分享一些编程相关的课程')],
  ['链接不含中文标点',    () => [...(bubble?.querySelectorAll('a.cs-link') || [])]
      .every(a => !/[，。、；！？一-鿿]/.test(a.getAttribute('href') || ''))],

  // Regression: the panel needs 540(h) + 76(button clearance) + 20(margin) = 636
  // tall and 360 + 20*2 = 400 wide. Hosts were sized 380x560, which clipped the
  // panel and let the iframe's own background show as a white block. Values are
  // read back from the CSS, so changing the panel size without updating the
  // embed docs / .chat-frame height fails here.
  ['iframe 尺寸要求仍是 400x636', () => {
    const num = (sel, prop) => {
      const i = src.indexOf(sel);
      const m = src.slice(i, src.indexOf('}', i))
                   .match(new RegExp(prop + '\\s*:\\s*(\\d+)px'));
      return m ? +m[1] : null;
    };
    const needH = num('.cs-pos-right {', 'bottom')
                + num('.cs-panel {', 'bottom')
                + num('.cs-panel {', 'height');
    const needW = num('.cs-panel {', 'width')
                + num('.cs-pos-right {', 'bottom') * 2;
    if (needH !== 636 || needW !== 400) {
      console.log(`\n  ⚠ 组件现在需要 ${needW}x${needH}，`
                + `请同步更新 embed 文档和 .chat-frame 高度`);
      return false;
    }
    return true;
  }],
];

let failed = 0;
for (const [name, fn] of checks) {
  let ok = false;
  try { ok = !!fn(); } catch { ok = false; }
  if (!ok) failed++;
  console.log(`  ${ok ? '✓' : '✗'} ${name}`);
}
if (failed) {
  console.log('\n--- 气泡实际内容 ---');
  console.log((bubble?.innerHTML || '(空)').slice(0, 600));
}
console.log(failed ? `\n❌ ${failed}/${checks.length} 项失败` : `\n✅ ${checks.length} 项全部通过`);
process.exit(failed ? 1 : 0);
