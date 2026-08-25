"""生成轻量索引版知识库：只含标题/链接/标签/一句话摘要。

用途：先用它验证「关键词 → 文章地址」的检索效果，成本约为全文版的 1/8。
"""
import json, re
from collections import defaultdict

SITE = "https://www.qqmu.com/"
raw = json.load(open("qqmu_full.json"))
posts, cats = raw["posts"], raw["categories"]

def one_line(p):
    """从正文提炼一句话简介（比 WordPress 那个 66 字截断的摘要更完整）。"""
    body = p.get("content") or ""
    body = re.sub(r"\[代码\].*", "", body, flags=re.S)
    body = re.sub(r"^#+ .*$", "", body, flags=re.M)      # 去标题行
    body = re.sub(r"代码片段.*", "", body, flags=re.S)
    body = re.sub(r"\s+", " ", body).strip()
    if not body:
        body = re.sub(r"\[&hellip;\]|\[…\]", "", p.get("excerpt", "")).strip()
    if len(body) > 200:
        cut = body[:200]
        i = max(cut.rfind("。"), cut.rfind("；"))
        body = cut[: i + 1] if i > 80 else cut + "…"
    return body

by_cat = defaultdict(list)
for p in posts:
    for c in (p["categories"] or ["未分类"]):
        by_cat[c].append(p)
cat_link = {c["name"]: c["link"] for c in cats}

out = ["# QQ沐编程 文章索引（轻量版）", "",
       f"收录 {len(posts)} 篇文章的标题、链接、标签与简介，用于按关键词快速定位文章。",
       "推荐文章时必须给出完整链接。资料中没有的内容请如实说明，不要编造。", ""]

for c in sorted(by_cat, key=lambda x: -len(by_cat[x])):
    items = sorted(by_cat[c], key=lambda p: p["date"], reverse=True)
    out.append(f"【{c}】")
    out.append(f"栏目地址：{cat_link.get(c, SITE)}　共 {len(items)} 篇")
    out.append("")
    for p in items:
        tags = f"｜标签：{'、'.join(p['tags'])}" if p["tags"] else ""
        out.append(f"- {p['title']}")
        out.append(f"  链接：{p['link']}{tags}")
        s = one_line(p)
        if s:
            out.append(f"  简介：{s}")
    out.append("")

text = "\n".join(out)
open("kb_index_lite.md", "w").write(text)
print(f"✓ kb_index_lite.md  {len(text):,} 字符")
