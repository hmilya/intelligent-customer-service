"""批量抓取 QQ沐编程 全部文章正文。"""
import html as htmllib, json, re, sys, time, urllib.request

BASE = "https://www.qqmu.com/wp-json/wp/v2"
UA = {"User-Agent": "Mozilla/5.0 (compatible; KB-Builder/1.0)"}

def get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries - 1:
                print(f"\n  ! {url[:80]}: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (i + 1))

def clean(raw):
    """HTML → 可读纯文本，保留代码块与段落结构。"""
    if not raw:
        return ""
    s = raw
    # 代码块单独成段，避免和正文黏在一起
    s = re.sub(r"<pre[^>]*>(.*?)</pre>", lambda m: "\n[代码]\n" + m.group(1) + "\n", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|h[1-6]|li|tr|blockquote)>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    # 标题保留层级感
    for lvl in range(1, 7):
        s = re.sub(rf"<h{lvl}[^>]*>", f"\n{'#' * min(lvl + 1, 6)} ", s, flags=re.I)
    s = re.sub(r"<script.*?</script>", "", s, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", "", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s)
    s = s.replace(" ", " ").replace("​", "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return "\n".join(ln.rstrip() for ln in s.split("\n")).strip()

raw = json.load(open("qqmu_raw.json"))
by_id = {p["id"]: p for p in raw["posts"]}

print(f"抓取 {len(by_id)} 篇正文（每批 100 篇）…")
got, page = 0, 1
while True:
    batch = get(f"{BASE}/posts?per_page=100&page={page}&_fields=id,content")
    if not batch:
        break
    for item in batch:
        pid = item.get("id")
        if pid in by_id:
            by_id[pid]["content"] = clean(item.get("content", {}).get("rendered", ""))
            got += 1
    print(f"\r  已抓取正文 {got}/{len(by_id)}…", end="", flush=True)
    if len(batch) < 100:
        break
    page += 1
    time.sleep(0.3)
print()

# 页面正文
print("抓取页面正文…")
pg_by_id = {g["id"]: g for g in raw["pages"]}
page = 1
while True:
    batch = get(f"{BASE}/pages?per_page=100&page={page}&_fields=id,content")
    if not batch:
        break
    for item in batch:
        if item.get("id") in pg_by_id:
            pg_by_id[item["id"]]["content"] = clean(item.get("content", {}).get("rendered", ""))
    if len(batch) < 100:
        break
    page += 1
print(f"  完成")

missing = [p["title"] for p in raw["posts"] if not p.get("content")]
lens = [len(p.get("content", "")) for p in raw["posts"] if p.get("content")]
json.dump(raw, open("qqmu_full.json", "w"), ensure_ascii=False)
total = sum(lens)
print(f"\n✓ qqmu_full.json 已保存")
print(f"  有正文 {len(lens)}/{len(raw['posts'])} 篇，缺失 {len(missing)} 篇")
print(f"  正文总量 {total:,} 字（约 {total/10000:.0f} 万字）")
if lens:
    lens.sort()
    print(f"  单篇长度: 最短 {lens[0]} / 中位 {lens[len(lens)//2]} / 最长 {lens[-1]}")
if missing[:5]:
    print(f"  缺失示例: {missing[:5]}")
