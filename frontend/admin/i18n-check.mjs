#!/usr/bin/env node
/**
 * Admin console i18n coverage check.
 *
 * Extracts every msgid the markup actually asks for (data-i18n textContent,
 * data-i18n-html innerHTML, data-i18n-attr attribute values) across every admin
 * page and asserts each one has an entry in all three catalogs in i18n.js.
 *
 * Why this exists: the msgid *is* the Chinese source text, so editing a label
 * in index.html silently orphans its translations — the page keeps working and
 * just renders Chinese to Japanese visitors. Nothing else would catch that.
 * A missing key is a real defect, not a warning.
 *
 * Also verifies data-i18n-html translations keep their inline tags, since
 * dropping a <code> would silently delete content from the page.
 *
 * Usage: node i18n-check.mjs
 */
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
// login.html is scanned alongside the console: it is a standalone page with its
// own inline script, so its labels and error toasts would otherwise be the one
// corner of the admin UI where an untranslated string goes unnoticed.
const PAGES = ['index.html', 'login.html'];
const html = PAGES.map((f) => readFileSync(join(here, f), 'utf8')).join('\n');
const norm = (s) => s.replace(/\s+/g, ' ').trim();

/**
 * Decode the entities a browser would, for msgids read back via textContent.
 *
 * `<option data-i18n>… Q&amp;A 切 …</option>` is `Q&A 切` by the time apply()
 * sees it, so a catalog keyed on `Q&amp;A` never matches. Attribute values go
 * through the same decoding. innerHTML msgids do NOT — there the entity text
 * is what comes back out.
 */
const decode = (s) => s
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'")
  .replace(/&nbsp;/g, ' ')
  .replace(/&amp;/g, '&');       // last, so &amp;lt; does not become <
const text = (s) => decode(norm(s));

// Scan the whole document with <style> and <script> bodies removed, rather than
// slicing at the first "<script": the page now loads locale.js and i18n.js from
// the <head>, and <title data-i18n> sits above them.
const body = html
  .replace(/<style[\s\S]*?<\/style>/gi, '')
  .replace(/<script[\s\S]*?<\/script>/gi, '');

// --- what the markup asks for -------------------------------------------------
const wantText = [];
const wantHtml = [];
const wantAttr = [];

for (const m of body.matchAll(
  /<([a-z][a-z0-9]*)((?:[^<>"]|"[^"]*")*?)\bdata-i18n\b(?!-)((?:[^<>"]|"[^"]*")*)>([^<>]*)<\/\1>/g)) {
  const s = text(m[4]);
  if (s) wantText.push(s);
}
for (const m of body.matchAll(
  /<([a-z]+)(?:[^<>"]|"[^"]*")*?\bdata-i18n-html\b(?:[^<>"]|"[^"]*")*>([\s\S]*?)<\/\1>/g)) {
  const s = norm(m[2]);
  if (s) wantHtml.push(s);
}
for (const m of body.matchAll(
  /<[a-z]+((?:[^<>"]|"[^"]*")*?)\bdata-i18n-attr="([^"]*)"((?:[^<>"]|"[^"]*")*)>/g)) {
  const attrs = m[1] + m[3];
  for (const name of m[2].split(',')) {
    const v = new RegExp(name.trim() + '="([^"]*)"').exec(attrs);
    if (v) wantAttr.push(text(v[1]));
  }
}

// --- what the runtime script asks for ----------------------------------------
// Toasts, status text and JS-built tables go through T('中文'). Those msgids
// never appear in the markup, so without this the page would switch to English
// and still pop Chinese toasts.
const wantRuntime = [];
{
  const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)]
    .map((m) => m[1]).join('\n');
  // T('…') / T("…") / T(`…`). A backtick msgid with ${} in it would be a bug
  // (the interpolation happens before lookup), so those are reported too.
  for (const m of scripts.matchAll(/\bT\(\s*(['"`])((?:\\.|(?!\1)[^\\])*)\1/g)) {
    // Unescape the way the JS engine would: the catalog key has to be the
    // runtime value, so '\n请确认…' must be keyed on a real newline.
    const s = m[2].replace(/\\(n|t|r|\\|'|"|`)/g, (_, c) =>
      ({ n: '\n', t: '\t', r: '\r' })[c] || c);
    if (/[一-鿿぀-ヿ]/.test(s)) wantRuntime.push(s);
  }
}

// --- what the catalogs provide -----------------------------------------------
// Load i18n.js for real rather than regex-scraping it, so duplicate keys and
// syntax errors surface the same way the browser would see them.
const src = readFileSync(join(here, 'i18n.js'), 'utf8');
// Minimal DOM stub: this check only exercises t()/setLang() lookups, so the
// mount() path just needs to not throw.
const noop = () => {};
const stubEl = {
  textContent: '', classList: { add: noop, remove: noop, toggle: () => false },
  setAttribute: noop, getAttribute: () => null, addEventListener: noop,
  appendChild: noop, childNodes: [],
};
const sandbox = {
  localStorage: null,
  location: { href: 'http://localhost/' },
  document: {
    readyState: 'complete',
    documentElement: { setAttribute: noop },
    querySelectorAll: () => [],
    getElementById: () => null,
    createElement: () => ({ ...stubEl }),
    addEventListener: noop,
    dispatchEvent: noop,
  },
  CustomEvent: function () {},
};
new Function('window', src + '\n;return window;')(sandbox);
const I18N = sandbox.CSAdminI18n;
if (!I18N) {
  console.error('✗ i18n.js did not define CSAdminI18n');
  process.exit(1);
}

const LANGS = ['zh-TW', 'ja', 'en'];
const all = [...new Set([...wantText, ...wantHtml, ...wantAttr, ...wantRuntime])];

const missing = {};
for (const lang of LANGS) {
  // Presence, not t(k) !== k: 微信, 保存 and Embedding 模型 are spelled the same
  // in Traditional Chinese / Japanese, so an identical value is a legitimate
  // translation. Only an absent key means nobody looked at it.
  missing[lang] = all.filter((k) => !I18N.has(k, lang));
}

// A translation must keep every inline tag its msgid had, or the page silently
// loses content when that language is selected. Runtime T() msgids carry markup
// too (JS-built <li>, <option>, <span style>), so they are checked as well.
const tagBugs = [];
for (const lang of LANGS) {
  I18N.setLang(lang);
  for (const k of [...new Set([...wantHtml, ...wantRuntime])]) {
    const want = (k.match(/<(code|strong|a|em|b|li|span|div|option|br|tr|td|th)\b/g) || []).sort();
    const got = (I18N.t(k).match(/<(code|strong|a|em|b|li|span|div|option|br|tr|td|th)\b/g) || []).sort();
    if (want.join() !== got.join()) {
      tagBugs.push(`  [${lang}] ${k.slice(0, 60)}…\n     tags ${want.join()} → ${got.join()}`);
    }
  }
}

// fmt() fills {0}, {1}… after the lookup. A translation that drops one loses a
// filename or a count; one that invents an extra renders a literal "{2}".
const slotBugs = [];
for (const lang of LANGS) {
  I18N.setLang(lang);
  for (const k of all) {
    const want = (k.match(/\{\d+\}/g) || []).sort();
    if (!want.length) continue;
    const got = (I18N.t(k).match(/\{\d+\}/g) || []).sort();
    if (want.join() !== got.join()) {
      slotBugs.push(`  [${lang}] ${k.slice(0, 60)}…\n     ${want.join()} → ${got.join()}`);
    }
  }
}

// --- report -------------------------------------------------------------------
console.log(`msgids: ${all.length} `
          + `(markup text ${new Set(wantText).size}, html ${new Set(wantHtml).size}, `
          + `attr ${new Set(wantAttr).size}, runtime T() ${new Set(wantRuntime).size})`);

// `--dump <file>` writes every msgid out as JSON, for handing to translators.
const dumpAt = process.argv.indexOf('--dump');
if (dumpAt !== -1) {
  const out = process.argv[dumpAt + 1] || 'msgids.json';
  const { writeFileSync } = await import('fs');
  writeFileSync(out, JSON.stringify({
    html: [...new Set(wantHtml)],
    plain: all.filter((k) => !wantHtml.includes(k)),
    // Only the ones no catalog covers yet — that is what a translator needs.
    todo: Object.fromEntries(LANGS.map((l) => [l, missing[l]])),
  }, null, 1));
  console.log(`dumped → ${out}`);
}

let failed = 0;
for (const lang of LANGS) {
  const m = missing[lang];
  if (m.length) {
    failed++;
    console.log(`\n✗ ${lang}: ${m.length} untranslated`);
    m.forEach((k) => console.log('    ' + k.slice(0, 100)));
  } else {
    console.log(`✓ ${lang}: complete`);
  }
}
if (tagBugs.length) {
  failed++;
  console.log(`\n✗ inline tags dropped in ${tagBugs.length} translation(s):`);
  tagBugs.forEach((b) => console.log(b));
} else {
  console.log('✓ inline tags preserved in every translation');
}
if (slotBugs.length) {
  failed++;
  console.log(`\n✗ {n} placeholders altered in ${slotBugs.length} translation(s):`);
  slotBugs.forEach((b) => console.log(b));
} else {
  console.log('✓ {n} placeholders preserved in every translation');
}

console.log(failed ? '\n❌ i18n coverage incomplete' : '\n✅ i18n coverage complete');
process.exit(failed ? 1 : 0);
