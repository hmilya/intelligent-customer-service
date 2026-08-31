#!/usr/bin/env node
/**
 * 管理后台语言切换自检：在真实 DOM 里跑一遍「构建 → 应用 → 切换 → 切回」。
 *
 * 为什么需要这个：i18n-check.mjs 用正则从 HTML 里抠 msgid，只能证明「目录覆盖
 * 齐全」；它证明不了浏览器里 innerHTML 抠出来的 msgid 和目录的键真的对得上
 * （空白、实体、属性顺序都可能差一点），也证明不了连续切两次语言还能切回来。
 * 这个脚本用 jsdom 加载真正的 index.html，走真正的 apply() 路径。
 *
 * 用法：node selftest.mjs
 *
 * jsdom 从 ../widget/node_modules 借用（widget 已经把它列为 devDependency），
 * 免得为一个纯静态目录再装一份 node_modules。先跑一次 `cd ../widget && npm i`。
 */
import { createRequire } from 'module';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(join(here, '..', 'widget', 'package.json'));
let JSDOM;
try {
  ({ JSDOM } = require('jsdom'));
} catch (_) {
  console.error('缺少 jsdom：请先 cd ../widget && npm install');
  process.exit(1);
}

const html = readFileSync(join(here, 'index.html'), 'utf8');

/**
 * Fresh console in the given language.
 *
 * `runScripts: 'outside-only'` keeps the page's own <script> from running — it
 * would immediately fetch /api/config and fail. locale.js and i18n.js are
 * eval'd by hand instead, which is exactly what the <script src> tags do.
 *
 * The language is seeded through localStorage rather than by faking a timezone:
 * region detection has its own 28-case table in ../widget/selftest.mjs, and
 * `stored` is the highest-priority signal, so this stays deterministic.
 */
function boot(stored) {
  const dom = new JSDOM(html, { runScripts: 'outside-only', url: 'http://localhost:8000/admin/' });
  const { window } = dom;
  if (stored) window.localStorage.setItem('cs_lang', stored);
  window.eval(readFileSync(join(here, '..', 'shared', 'locale.js'), 'utf8'));
  window.eval(readFileSync(join(here, 'i18n.js'), 'utf8'));
  const I18N = window.CSAdminI18n;
  I18N.mount();                      // DOMContentLoaded never fires here
  return { window, doc: window.document, I18N };
}

/** All translatable nodes, keyed by the msgid the engine snapshotted. */
function byMsgid(doc) {
  const map = new Map();
  doc.querySelectorAll('[data-i18n]').forEach((el) => {
    if (el._csMsgid !== undefined) map.set(el._csMsgid, el);
  });
  return map;
}

const checks = [
  ['默认语言是简体中文（源语言，无目录）', () => {
    const { I18N, doc } = boot(null);
    // No stored choice and jsdom's timezone/navigator are whatever the host has,
    // so only assert the invariant: zh-CN leaves the markup untouched.
    I18N.setLang('zh-CN');
    return I18N.getLang() === 'zh-CN' &&
      doc.querySelector('[data-page="dashboard"] [data-i18n]').textContent.includes('概览');
  }],

  ['下拉里有四种语言，各用自己的文字', () => {
    const { doc } = boot(null);
    const items = [...doc.querySelectorAll('#langMenu button')];
    const codes = items.map((b) => b.getAttribute('data-lang')).join(',');
    const labels = items.map((b) => b.textContent).join(',');
    return codes === 'zh-CN,zh-TW,ja,en' && labels === '简体中文,繁體中文,日本語,English';
  }],

  ['下拉项带 lang 属性（让浏览器选对字体）', () => {
    const { doc } = boot(null);
    return [...doc.querySelectorAll('#langMenu button')]
      .every((b) => b.getAttribute('lang') === b.getAttribute('data-lang'));
  }],

  ['启动时就是存储里的语言（离线，无需网络）', () => {
    const { I18N, doc } = boot('ja');
    return I18N.getLang() === 'ja' &&
      doc.querySelector('[data-page="dashboard"] [data-i18n]').textContent === '概要';
  }],

  ['切到英语后侧边栏变英语', () => {
    const { I18N, doc } = boot(null);
    I18N.setLang('en');
    return doc.querySelector('[data-page="dashboard"] [data-i18n]').textContent === 'Dashboard' &&
      doc.querySelector('[data-page="llm"] [data-i18n]').textContent === 'Model Config';
  }],

  ['连续切两次仍然正确（msgid 快照生效）', () => {
    const { I18N, doc } = boot(null);
    const el = () => doc.querySelector('[data-page="llm"] [data-i18n]').textContent;
    I18N.setLang('en');
    if (el() !== 'Model Config') return 'en 阶段就错了：' + el();
    I18N.setLang('ja');       // 若用当前文本做键，这一步会查不到而卡在英文
    if (el() !== 'モデル設定') return 'ja 阶段错了：' + el();
    I18N.setLang('zh-TW');
    return el() === '模型設定' || 'zh-TW 阶段错了：' + el();
  }],

  ['切回简体中文能完全还原', () => {
    const { I18N, doc } = boot(null);
    const before = doc.body.textContent;
    I18N.setLang('ja');
    I18N.setLang('en');
    I18N.setLang('zh-CN');
    return doc.body.textContent === before;
  }],

  ['title 属性也被翻译', () => {
    const { I18N, doc } = boot(null);
    I18N.setLang('en');
    return doc.getElementById('btnCheckUpdate').getAttribute('title') ===
      'Check for a new version';
  }],

  ['<title> 跟着变', () => {
    const { I18N, doc } = boot(null);
    I18N.setLang('ja');
    return doc.title === 'AI カスタマーサポート · 管理コンソール';
  }],

  ['data-i18n-html 的内联标签在 DOM 里活着', () => {
    const { I18N, doc } = boot(null);
    I18N.setLang('en');
    const bad = [...doc.querySelectorAll('[data-i18n-html]')].filter((el) => {
      const want = (el._csMsgidHtml.match(/<(code|strong|a|em|b)\b/g) || []).length;
      return el.querySelectorAll('code,strong,a,em,b').length !== want;
    });
    return bad.length === 0 || bad.map((e) => e._csMsgidHtml.slice(0, 40));
  }],

  ['每个 msgid 在英语下都真的换了词', () => {
    // The strongest check here: proves the msgid the *browser* computes matches
    // the catalog key, whitespace and entities included.
    const { I18N, doc } = boot(null);
    I18N.setLang('en');
    const stale = [...byMsgid(doc).entries()]
      .filter(([msgid, el]) => /[一-鿿]/.test(msgid) && el.textContent === msgid)
      .map(([msgid]) => msgid);
    return stale.length === 0 || stale;
  }],

  ['按钮上的语言名跟着变', () => {
    const { I18N, doc } = boot(null);
    I18N.setLang('zh-TW');
    return doc.getElementById('langLabel').textContent === '繁體中文';
  }],

  ['语言名不是待翻译文本（不能带 data-i18n）', () => {
    // If it were marked, apply() would replace 简体中文 with *a translation of
    // it* and the button would say "Simplified Chinese" while showing English.
    // mark-i18n.py excludes it; this is the assertion that keeps it excluded.
    const { doc } = boot(null);
    return doc.getElementById('langLabel').hasAttribute('data-i18n') === false;
  }],

  ['<html lang> 同步（读屏与 CJK 字体要用）', () => {
    const { I18N, doc } = boot(null);
    I18N.setLang('ja');
    return doc.documentElement.getAttribute('lang') === 'ja';
  }],

  ['切换被持久化，下次进来还是它', () => {
    const { I18N, window } = boot(null);
    I18N.setLang('en');
    if (window.localStorage.getItem('cs_lang') !== 'en') return '没写进 localStorage';
    return boot('en').I18N.getLang() === 'en';
  }],

  ['当前语言在下拉里高亮', () => {
    const { I18N, doc } = boot(null);
    I18N.setLang('ja');
    const on = [...doc.querySelectorAll('#langMenu button')]
      .filter((b) => b.classList.contains('active'));
    return on.length === 1 && on[0].getAttribute('data-lang') === 'ja';
  }],

  ['聊天预览 iframe 带上 ?lang= 重载', () => {
    const { I18N, doc } = boot(null);
    const frame = doc.getElementById('chatFrame');
    frame.src = 'embed.html?api=http://localhost:8000';
    I18N.setLang('ja');
    return frame.src.includes('lang=ja') && frame.src.includes('api=');
  }],

  ['切换会派发 cs-lang-change 事件', () => {
    const { I18N, doc } = boot(null);
    let got = null;
    doc.addEventListener('cs-lang-change', (e) => { got = e.detail.lang; });
    I18N.setLang('en');
    return got === 'en';
  }],

  ['不认识的语言码被忽略，不会把页面弄空', () => {
    const { I18N, doc } = boot(null);
    I18N.setLang('en');
    I18N.setLang('de');
    return I18N.getLang() === 'en' &&
      doc.querySelector('[data-page="dashboard"] [data-i18n]').textContent === 'Dashboard';
  }],

  ['菜单点击真的能切换（走的是真事件）', () => {
    const { I18N, doc, window } = boot(null);
    const jaBtn = doc.querySelector('#langMenu button[data-lang="ja"]');
    jaBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    return I18N.getLang() === 'ja' &&
      doc.querySelector('[data-page="dashboard"] [data-i18n]').textContent === '概要';
  }],

  ['地球按钮开关菜单并同步 aria-expanded', () => {
    const { doc, window } = boot(null);
    const btn = doc.getElementById('langBtn');
    const menu = doc.getElementById('langMenu');
    const click = () => btn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    click();
    if (!menu.classList.contains('open') || btn.getAttribute('aria-expanded') !== 'true') {
      return '没打开';
    }
    click();
    return !menu.classList.contains('open') && btn.getAttribute('aria-expanded') === 'false';
  }],

  ['点页面别处会收起菜单', () => {
    const { doc, window } = boot(null);
    const btn = doc.getElementById('langBtn');
    const menu = doc.getElementById('langMenu');
    btn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    doc.body.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    return !menu.classList.contains('open');
  }],

  ['locale.js 缺失时退回中文而不是崩', () => {
    const dom = new JSDOM(html, { runScripts: 'outside-only', url: 'http://localhost:8000/admin/' });
    dom.window.eval(readFileSync(join(here, 'i18n.js'), 'utf8'));   // 只加载 i18n.js
    const I18N = dom.window.CSAdminI18n;
    I18N.mount();
    return I18N.getLang() === 'zh-CN' && I18N.LOCALES.length === 4;
  }],

  ['mount() 调两次不会出现重复下拉项', () => {
    const { doc, I18N } = boot(null);
    I18N.mount();
    return doc.querySelectorAll('#langMenu button').length === 4;
  }],
];

let pass = 0;
const fails = [];
for (const [name, fn] of checks) {
  let r;
  try { r = fn(); } catch (e) { r = 'THREW: ' + e.message; }
  if (r === true) { pass++; console.log('  ✓ ' + name); }
  else { fails.push([name, r]); console.log('  ✗ ' + name + '  → ' + JSON.stringify(r)); }
}

console.log(`\n${pass}/${checks.length} 通过`);
if (fails.length) {
  console.log('\n失败详情：');
  fails.forEach(([n, r]) => console.log('  ' + n + ': ' + JSON.stringify(r, null, 1)));
  process.exit(1);
}
console.log('✅ 管理后台语言切换正常');
