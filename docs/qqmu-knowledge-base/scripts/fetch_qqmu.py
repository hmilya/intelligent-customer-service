"""抓取 QQ沐编程 全站文章/页面/分类/标签元数据。"""
import json, re, sys, time, urllib.request, urllib.error

BASE = "https://www.qqmu.com/wp-json/wp/v2"
UA = {"User-Agent": "Mozilla/5.0 (compatible; KB-Builder/1.0)"}

def get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries - 1:
                print(f"  ! 失败 {url}: {e}", file=sys.stderr)
                return None
            time.sleep(1.5 * (i + 1))

def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
          .replace("&gt;", ">").replace("&quot;", '"').replace("&#8217;", "'")
          .replace("&#8211;", "-").replace("&#8230;", "…").replace("&#039;", "'"))
    return re.sub(r"\s+", " ", s).strip()

def fetch_all(endpoint, fields, per_page=100, label=""):
    out, page = [], 1
    while True:
        url = f"{BASE}/{endpoint}?per_page={per_page}&page={page}&_fields={fields}"
        batch = get(url)
        if not batch:
            break
        out.extend(batch)
        print(f"\r  {label} 已获取 {len(out)} 条…", end="", flush=True)
        if len(batch) < per_page:
            break
        page += 1
        time.sleep(0.25)   # 别把站点打疼
    print(f"\r  {label} 共 {len(out)} 条        ")
    return out

print("拉取分类…")
cats = fetch_all("categories", "id,name,slug,count,description,link", label="分类")
print("拉取标签…")
tags = fetch_all("tags", "id,name,slug,count,link", label="标签")
print("拉取文章（2095 篇，约需 1-2 分钟）…")
posts = fetch_all("posts", "id,date,modified,link,title,excerpt,categories,tags", label="文章")
print("拉取页面…")
pages = fetch_all("pages", "id,link,title,excerpt,date", label="页面")

cat_by_id = {c["id"]: c["name"] for c in cats}
tag_by_id = {t["id"]: t["name"] for t in tags}

data = {
    "categories": [
        {"id": c["id"], "name": c["name"], "slug": c["slug"], "count": c["count"],
         "link": c["link"], "description": strip_html(c.get("description", ""))}
        for c in cats
    ],
    "tags": [
        {"id": t["id"], "name": t["name"], "slug": t["slug"], "count": t["count"], "link": t["link"]}
        for t in tags if t["count"] > 0
    ],
    "posts": [
        {"id": p["id"], "title": strip_html(p["title"]["rendered"]), "link": p["link"],
         "date": (p.get("date") or "")[:10], "modified": (p.get("modified") or "")[:10],
         "excerpt": strip_html(p.get("excerpt", {}).get("rendered", ""))[:400],
         "categories": [cat_by_id.get(i, "") for i in p.get("categories", []) if cat_by_id.get(i)],
         "tags": [tag_by_id.get(i, "") for i in p.get("tags", []) if tag_by_id.get(i)]}
        for p in posts
    ],
    "pages": [
        {"id": g["id"], "title": strip_html(g["title"]["rendered"]), "link": g["link"],
         "excerpt": strip_html(g.get("excerpt", {}).get("rendered", ""))[:300]}
        for g in pages
    ],
}
json.dump(data, open("qqmu_raw.json", "w"), ensure_ascii=False, indent=1)
print(f"\n✓ 已保存 qqmu_raw.json")
print(f"  分类 {len(data['categories'])} · 标签 {len(data['tags'])} · 文章 {len(data['posts'])} · 页面 {len(data['pages'])}")
