"""把抓取结果编译成结构感知切分器友好的知识库 Markdown。

产出结构刻意配合本项目的 structure-aware splitter：
  【章节】 → 每篇文章一个独立 chunk，标题会被带进 chunk 前缀
"""
import json, re
from collections import defaultdict

SITE = "https://www.qqmu.com/"
MAX_BODY = 1600          # 单篇正文保留上限（字）；超长基本是代码堆积
MAX_CODE_PEEK = 260      # 代码块只留开头示意

raw = json.load(open("qqmu_full.json"))
posts, cats, tags, pages = raw["posts"], raw["categories"], raw["tags"], raw["pages"]

def condense(text):
    """压缩正文：去掉站点噪音、裁剪代码块、限制总长。"""
    if not text:
        return ""
    # 站点通用噪音
    noise = [
        r"温馨提示[:：].{0,80}", r"本站.{0,40}(资源|源码).{0,60}", r"如有侵权.{0,60}",
        r"未经允许不得转载.{0,40}", r"声明[:：].{0,80}", r"版权归原作者所有.{0,40}",
        r"下载地址[:：]?\s*$", r"关注公众号.{0,40}", r"扫码.{0,30}",
    ]
    for pat in noise:
        text = re.sub(pat, "", text, flags=re.I)

    # 代码块只留开头，避免上千行 JS 淹没说明文字
    def trim_code(m):
        code = m.group(1).strip()
        if len(code) <= MAX_CODE_PEEK:
            return f"\n代码片段：\n{code}\n"
        return f"\n代码片段（节选，完整代码见原文）：\n{code[:MAX_CODE_PEEK]}…\n"
    text = re.sub(r"\[代码\]\n(.*?)(?=\n\n|\n#|\Z)", trim_code, text, flags=re.S)

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > MAX_BODY:
        cut = text[:MAX_BODY]
        # 尽量断在句子边界
        for sep in ("\n\n", "。", "\n", "；"):
            i = cut.rfind(sep, MAX_BODY // 2)
            if i > 0:
                cut = cut[: i + len(sep)]
                break
        text = cut.rstrip() + "\n（以上为文章主要内容节选，完整内容请访问原文链接）"
    return text

# ── 按分类归组 ───────────────────────────────────────────
by_cat = defaultdict(list)
for p in posts:
    for c in (p["categories"] or ["未分类"]):
        by_cat[c].append(p)
cat_order = sorted(by_cat, key=lambda c: -len(by_cat[c]))
cat_desc = {c["name"]: c["description"] for c in cats}
cat_link = {c["name"]: c["link"] for c in cats}

out = []
w = out.append

# ═══ 文件 1：主知识库 ═══
w("# QQ沐编程 知识库")
w("")
w("【网站简介】")
w(f"QQ沐编程（{SITE}）是一个面向编程学习者与开发者的技术资源站，"
  f"提供源码项目、网页特效、技术教程、编程课程和实用软件工具。"
  f"目前收录 {len(posts)} 篇文章，覆盖 {len(cats)} 个分类。")
w("")
w("回答用户问题时的要求：")
w("1. 推荐文章必须给出完整的原文链接（形如 https://www.qqmu.com/数字.html）。")
w("2. 用户描述需求（如「想找一个登录页面模板」）时，匹配最相关的文章并说明它能解决什么。")
w("3. 资料里没有的内容不要编造，如实告知并建议访问网站搜索。")
w("")

# ── 分类导航 ──
w("【网站栏目一览】")
w("用户问「有哪些分类」「网站都有什么内容」时参考下表。")
w("")
w("| 栏目 | 文章数 | 栏目地址 |")
w("|---|---|---|")
for c in cat_order:
    w(f"| {c} | {len(by_cat[c])} | {cat_link.get(c, SITE)} |")
w("")

# ── 关键词 → 栏目映射（帮助模糊匹配）──
w("【关键词与栏目对应关系】")
w("用户用不同说法描述同一需求时，按下表映射到对应栏目。")
w("")
KEYWORD_MAP = [
    ("HTML项目", "网页模板、静态页面、前端页面、H5、企业官网模板、个人主页、登录页面、注册页面"),
    ("网页特效", "JS特效、CSS动画、鼠标特效、背景动画、轮播图、滚动效果、粒子效果、雪花樱花飘落"),
    ("html模块", "网页组件、页面模块、导航栏、页脚、侧边栏、弹窗、卡片"),
    ("404模板", "404页面、错误页面、找不到页面、报错页面"),
    ("PHP项目", "PHP源码、后台管理系统、PHP网站、留言板、CMS"),
    ("python项目", "Python源码、爬虫项目、自动化脚本、数据分析、GUI程序、桌面工具"),
    ("python小案例", "Python练习、Python入门例子、小程序练习、Python习题"),
    ("python脚本", "Python实用脚本、批处理、自动化"),
    ("python课程", "Python教学、Python视频课、Python系统学习"),
    ("java项目", "Java源码、SSM、SpringBoot、管理系统、JavaWeb"),
    ("java小案例", "Java练习题、Java入门例子、Java基础案例"),
    ("java工具类", "Java工具方法、Utils、公共类"),
    ("java课程", "Java教学、Java视频课"),
    ("C语言项目", "C语言源码、C语言大作业、C语言管理系统"),
    ("C语言小案例", "C语言练习、C语言入门题、C语言基础例子"),
    ("C++小案例", "C++练习、C++入门例子、C++基础"),
    ("vue项目", "Vue源码、Vue后台、ElementUI、前端框架项目"),
    ("小程序项目", "微信小程序、小程序源码、uniapp"),
    ("技术教程", "怎么做、如何配置、教程、指南、部署、安装、解决方法"),
    ("编程课程", "视频课程、系统学习、课程资源、学习路线"),
    ("电脑软件", "PC软件、Windows工具、破解版、绿色软件、效率工具"),
    ("手机软件", "APP、安卓应用、手机工具、iOS"),
    ("BUG专区", "报错、异常、错误、修复、踩坑、无法启动、闪退"),
    ("GIT相关知识", "Git、GitHub、Gitee、版本控制、代码托管、提交冲突"),
    ("工具推荐", "好用的工具、软件推荐、插件推荐"),
    ("实用脚本", "脚本、自动化、批量处理"),
    ("模块代码", "代码片段、通用代码、复用代码"),
    ("项目专区", "完整项目、毕业设计、课程设计、实战项目"),
    ("新媒体运营", "运营、公众号、自媒体、流量"),
    ("随心随笔", "随笔、感想、经验分享、日志"),
    ("游戏相关", "游戏、小游戏、游戏源码"),
    ("摄影剪辑", "摄影、视频剪辑、后期"),
    ("编程小作业", "作业、练习题、课后题"),
]
w("| 栏目 | 用户可能的说法（关键词） |")
w("|---|---|")
for name, kws in KEYWORD_MAP:
    if name in by_cat:
        w(f"| {name} | {kws} |")
w("")

# ── 热门标签 ──
top_tags = sorted([t for t in tags if t["count"] >= 5], key=lambda t: -t["count"])
w("【热门标签】")
w("按技术栈/主题检索时可参考（格式：标签名(文章数)）。")
w("")
w("，".join(f"{t['name']}({t['count']})" for t in top_tags[:120]))
w("")

json.dump({"cat_order": cat_order}, open("_meta.json", "w"))
open("kb_main.md", "w").write("\n".join(out))
print(f"✓ kb_main.md  {sum(len(x) for x in out):,} 字符")

# ═══ 文件 2..N：按分类拆分的文章详情 ═══
def slugify(name):
    return re.sub(r"[^\w一-龥]+", "_", name).strip("_")

files = []
for c in cat_order:
    items = sorted(by_cat[c], key=lambda p: p["date"], reverse=True)
    buf = [f"# QQ沐编程 · {c}"]
    buf.append("")
    buf.append(f"本文件收录「{c}」栏目下的 {len(items)} 篇文章。栏目地址：{cat_link.get(c, SITE)}")
    if cat_desc.get(c):
        buf.append(f"栏目说明：{cat_desc[c]}")
    buf.append("")
    for p in items:
        # 【标题】让结构感知切分器把每篇文章切成独立 chunk
        buf.append(f"【{p['title']}】")
        buf.append(f"文章地址：{p['link']}")
        buf.append(f"所属栏目：{'、'.join(p['categories'])}")
        if p["tags"]:
            buf.append(f"标签：{'、'.join(p['tags'])}")
        buf.append(f"发布日期：{p['date']}")
        body = condense(p.get("content", "")) or p.get("excerpt", "")
        if body:
            # 正文里的小标题会被切分器切成独立 chunk，那些 chunk 就看不到
            # 上面的「文章地址」行了。在每个小节后补一行链接，保证任何片段
            # 被检索到时模型都能给出出处。
            body = re.sub(
                r"^(#{2,6} .+)$",
                lambda m: f"{m.group(1)}\n（本节出自：{p['link']}）",
                body,
                flags=re.M,
            )
            buf.append("")
            buf.append(body)
        buf.append("")
    fn = f"kb_cat_{slugify(c)}.md"
    text = "\n".join(buf)
    open(fn, "w").write(text)
    files.append((fn, c, len(items), len(text)))

# ═══ 文件：独立页面 ═══
if pages:
    buf = ["# QQ沐编程 · 站点页面", "",
           "网站的独立页面（关于、联系、导航等非文章内容）。", ""]
    for g in pages:
        buf.append(f"【{g['title']}】")
        buf.append(f"页面地址：{g['link']}")
        body = condense(g.get("content", "")) or g.get("excerpt", "")
        if body:
            buf.append("")
            buf.append(body)
        buf.append("")
    open("kb_pages.md", "w").write("\n".join(buf))
    files.append(("kb_pages.md", "站点页面", len(pages), sum(len(x) for x in buf)))

print(f"\n生成 {len(files)} 个分类文件:")
for fn, c, n, size in files:
    print(f"  {fn:52s} {n:5d} 篇  {size:>9,} 字符")
print(f"\n总计 {sum(f[3] for f in files):,} 字符")
