# 🤖 智能客服系统（Intelligent Customer Service）

**简体中文** · [English](README.en.md)

> 基于 **FastAPI + RAG** 的多模型智能客服平台。
> **装完依赖点一下运行，剩下全在网页上配** —— 不改配置文件，不跑初始化脚本。

![status](https://img.shields.io/badge/status-可用-brightgreen)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![tests](https://img.shields.io/badge/tests-36%20backend%20%2B%2017%20widget-brightgreen)
![license](https://img.shields.io/badge/license-MIT-green)

**仓库地址**

| 平台 | 地址 | 说明 |
| --- | --- | --- |
| GitHub | https://github.com/vfaner/intelligent-customer-service | 主仓库，Issue / PR 请提到这里 |
| Gitee | https://gitee.com/super_rgh/intelligent-customer-service | 国内镜像，克隆更快，只做同步不接受 PR |

---

## 目录

- [三步跑起来](#三步跑起来)
- [效果预览](#效果预览)
- [核心特性](#核心特性)
- [页面导览](#页面导览)
- [架构](#架构)
- [目录结构](#目录结构)
- [支持的模型厂商](#支持的模型厂商)
- [向量数据库](#向量数据库)
- [智能分词（结构感知切分）](#智能分词结构感知切分)
- [回答策略：严格 RAG 还是允许自主回答](#回答策略严格-rag-还是允许自主回答)
- [嵌入到你的网站](#嵌入到你的网站)
- [API 速查](#api-速查)
- [配置项参考](#配置项参考)
- [常见问题](#常见问题)
- [开发与测试](#开发与测试)
- [生产部署](#生产部署)

---

## 三步跑起来

### 1. 装依赖

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 启动

**PyCharm**：右键 `backend/run.py` → **Run**

**命令行**：

```bash
python run.py
```

启动后会打印：

```
==============================================================
  🤖 IntelligentCustomerService
==============================================================
  ⚙️  管理后台   http://localhost:8000/admin/     ← 从这里开始
  🪟  组件演示   http://localhost:8000/widget/demo/
  📖  API 文档   http://localhost:8000/docs
--------------------------------------------------------------
  ⚠  尚未配置对话模型 API Key
     → 打开管理后台「模型配置」填写即可，无需改文件
==============================================================
```

> 缺依赖时会提示**当前解释器**对应的安装命令；也可以 `python run.py --install` 自动装。

### 3. 打开管理后台配置

浏览器访问 **http://localhost:8000/admin/**

| 顺序 | 做什么 |
|---|---|
| 1️⃣ | 页面顶部若出现黄色横幅 → 点 **「🚀 一键初始化」**（建表 + 建目录 + 写默认配置） |
| 2️⃣ | 进 **「模型配置」** → 选厂商 → 填 API Key → **「🔌 测试连接」** → **「💾 保存」** |
| 3️⃣ | 同页 **「🧬 向量模型」** → **「⬆︎ 复用对话模型的 Key / URL」** → **「🔌 测试并探测维度」** |
| 4️⃣ | 进 **「知识文档」** → 拖入 txt/md/docx/xlsx/pdf → 自动解析入库 |
| 5️⃣ | 进 **「聊天预览」** → 直接提问验证 |

**完全不需要**编辑 `.env`、执行 `init_db.py` 或任何脚本。

<details>
<summary>命令行参数</summary>

```bash
python run.py --port 9000        # 换端口
python run.py --host 0.0.0.0     # 允许局域网访问
python run.py --no-reload        # 关闭热重载
python run.py --open             # 启动后自动打开浏览器
python run.py --install          # 缺依赖时自动安装
```

也支持标准 uvicorn：`uvicorn src.main:app --reload --port 8000`
</details>

---

## 效果预览

<table>
<tr>
<td width="50%"><b>🤖 模型配置</b><br>15 项厂商预设，选厂商自动填 Base URL 和模型；带连接测试与维度探测</td>
<td width="50%"><b>🔍 RAG 设置</b><br>回答策略开关、检索参数、切分策略，还能预览切分效果</td>
</tr>
<tr>
<td><img src="frontend/assets/ai_kefu_model.png" alt="模型配置"></td>
<td><img src="frontend/assets/ai_kefu_rag.png" alt="RAG 设置"></td>
</tr>
<tr>
<td><b>🧠 向量库</b><br>Chroma / Qdrant / Milvus 三选一，各自参数按需显示</td>
<td><b>💬 客服信息</b><br>名称、头像、欢迎语、联系方式，改一次对所有已嵌入站点生效</td>
</tr>
<tr>
<td><img src="frontend/assets/ai_kefu_xl.png" alt="向量库配置"></td>
<td><img src="frontend/assets/ai_kefu_config.png" alt="客服信息"></td>
</tr>
<tr>
<td><b>🪟 聊天预览</b><br>后台内直接测 RAG 问答，答案带 Markdown 渲染和可点击链接</td>
<td><b>🌐 嵌入指南</b><br>script / iframe / 小程序三种方式，代码一键复制</td>
</tr>
<tr>
<td><img src="frontend/assets/ai_kefu_view.png" alt="聊天预览"></td>
<td><img src="frontend/assets/ai_kefu_jieru.png" alt="嵌入指南"></td>
</tr>
</table>

**嵌入到网站后的实际效果** —— 右下角浮动按钮，点击弹出聊天窗口：

<p align="center">
  <img src="frontend/assets/ai_kefu_yanshi.png" alt="页面嵌入效果" width="720">
</p>

---

## 核心特性

| 模块 | 能力 |
|---|---|
| **📄 文档知识库** | `txt` / `md` / `docx` / `xlsx` / `pdf` 解析 → 结构感知切分 → 向量化 → 入库；MD5 去重；**断点续传** |
| **🧠 智能分词** | 识别`【章节】`、Markdown 标题、`第X章`、Q&A、Excel 工作表，沿语义边界切分，每片带标题上下文 |
| **🤖 多模型** | 15 项厂商配置：DeepSeek、千问/百炼、火山方舟（包月/按量分开）、智谱、Kimi、千帆、OpenAI、Claude、Gemini、Ollama、胜算云、优云智算、2 个自定义 |
| **🔁 双协议** | OpenAI `/chat/completions` 与 Anthropic `/messages` 可切换；切协议自动更新 Base URL |
| **🗂 三种向量库** | **Chroma**（默认，本地文件）/ **Qdrant** / **Milvus**（含 Lite 零安装） |
| **🎯 回答策略可选** | 默认严格 RAG（资料外一律拒答）；可开关允许 AI 自主回答 |
| **⚡ 流式输出** | SSE 实时 token；429 自动重试不中断 |
| **🪟 可嵌入组件** | 单文件 JS（零依赖、免构建），内置 Markdown 渲染 + 链接可点击 |
| **📲 跨平台** | 网站 / 微信小程序 `web-view` / Electron / Tauri / iOS / Android |
| **⚙️ 全网页配置** | 模型、向量库、RAG 参数、客服信息全部页面可改，改完即生效无需重启 |

---

## 页面导览

打开 `/admin/` 后左侧 8 个菜单：

| 菜单 | 作用 |
|---|---|
| 📊 **概览** | 系统状态、当前模型、向量库、文档数 |
| 🤖 **模型配置** | 对话模型（厂商/协议/Key/模型/温度）+ 向量模型；带连接测试与**维度自动探测** |
| 🧠 **向量库** | Chroma / Qdrant / Milvus 切换及各自参数 |
| 🔍 **RAG 设置** | **回答策略开关** + Top-K/阈值 + 切分策略；带**切分预览** |
| 📄 **知识文档** | 拖拽上传、**实时入库进度**、失败可续传、删除 |
| 💬 **客服信息** | 客服名称、头像、欢迎语、联系方式（组件自动读取） |
| 🪟 **聊天预览** | iframe 内嵌真实组件，直接测 RAG 问答 |
| 🌐 **嵌入指南** | 三种嵌入方式的代码，一键复制 |

页面右上角还有三个常驻工具：

| 工具 | 说明 |
|---|---|
| 🟢 **后端状态** | 每 15 秒自检一次。离线时鼠标悬停可看完整错误 |
| ⬆︎ **检测更新** | 比对当前版本与 GitHub 最新 Release，有新版时按钮上出现红点 |
| ☕ **打赏支持** | 微信 / 支付宝 / QQ 赞赏码 |

> **检测更新需要先配置仓库**：在 `backend/.env` 里加 `APP_GITHUB_REPO=owner/repo`。
> 未配置时按钮会给出配置指引，不会报错。
>
> 它**只检测不改代码** —— 发现新版会展示更新说明和更新命令，由你决定何时执行。
> 自动 `git pull` 会覆盖本地未提交的修改，还可能因依赖变更导致服务起不来，
> 不适合放在一个按钮后面。

---

## 架构

```
┌──────────── 浏览器 ────────────┐        ┌─────────── FastAPI 后端 ───────────┐
│  customer-service.js（零依赖）  │  HTTP  │  api · services · adapters          │
│   浮动按钮 + 聊天窗 + 文件上传  │ ◀────▶ │  vector_store · embeddings          │
│   SSE 流式 + Markdown 渲染     │  SSE   │  parsers · prompts · models         │
└────────────────────────────────┘        └──┬────────┬──────────┬─────────────┘
                                             │        │          │
                                        SQLite    Chroma /    LLM 厂商
                                        /MySQL    Qdrant /    (15 项配置)
                                        (会话)    Milvus
```

**LLM 适配器**（async + SSE，429 自动重试）：

```
BaseProvider
  ├── OpenAIStyleProvider     → POST {base}/chat/completions
  └── AnthropicStyleProvider  → POST {base}/messages
                                （system 为顶级字段；同时发 x-api-key 与
                                  Authorization: Bearer 以兼容各家网关）
build_provider() 按 protocol 分发
```

---

## 目录结构

```
intelligent-customer-service/
├── backend/
│   ├── run.py                        ← 一键启动（PyCharm 右键 Run）
│   ├── requirements.txt
│   ├── .env.example                  （可选；页面配置优先于此）
│   ├── docker-compose.yml            MySQL + Redis + Qdrant + Milvus
│   ├── src/
│   │   ├── main.py                   FastAPI app factory
│   │   ├── api/                      admin · chat · config · documents · models · sessions
│   │   ├── services/                 document · rag · llm · embedding · session
│   │   ├── adapters/                 base · openai · anthropic · factory
│   │   ├── vector_store/             base · chroma · qdrant · milvus · factory
│   │   ├── embeddings/               base · openai_compatible_embedder
│   │   ├── parsers/                  txt(含 md) · docx · xlsx · pdf
│   │   ├── prompts/system_prompts.py RAG 约束 + 自主回答提示词
│   │   ├── models/                   SQLAlchemy ORM
│   │   ├── core/                     config · database · registry · exceptions
│   │   ├── utils/                    text_splitter（结构感知）· sse · hash · obfuscation
│   │   └── tests/                    36 个测试
│   ├── scripts/
│   │   ├── init_db.py                建表（一键初始化已覆盖，一般不用手跑）
│   │   ├── check_env.py              依赖/配置自检
│   │   ├── ingest_docs.py            批量导入
│   │   └── ingest_retry.py           ← 大知识库自动重试入库
│   └── samples/                      示例知识文档
├── frontend/
│   ├── admin/
│   │   ├── index.html                管理后台
│   │   └── embed.html                独立聊天页（预览 / iframe 用）
│   └── widget/
│       ├── customer-service.js       嵌入组件（零依赖）
│       ├── selftest.mjs              ← 组件自检（17 项断言）
│       └── demo/                     嵌入演示
└── docs/
    ├── API.md · DEPLOYMENT.md · EMBED_GUIDE.md
    └── qqmu-knowledge-base/          示例知识库（脚本可重新生成）
```

---

## 支持的模型厂商

页面下拉按「厂商 / 自定义」分组，选厂商自动填 Base URL 和默认模型；点 🔄 可从你的账号拉取**真实可用**的模型列表。

| 厂商 | 协议 | 说明 |
|---|---|---|
| DeepSeek（深度求索） | openai | 性价比高 |
| 阿里云 · 通义千问 / 百炼 | openai | 共用 DashScope 兼容地址 |
| 火山方舟 · **包月套餐** | openai + anthropic | `/api/plan/v3`、`/api/plan/v1`，模型填 `ark-code-latest` |
| 火山方舟 · **豆包**（按量） | openai | `/api/v3` |
| 智谱 GLM | openai | |
| Kimi（Moonshot） | openai | |
| 百度千帆（ERNIE） | openai | v2 端点 |
| OpenAI | openai | 国内需代理 |
| Anthropic Claude | anthropic | 官方 Messages 协议 |
| 胜算云（模型路由） | openai | 聚合多家 |
| 优云智算 ⚠ | openai | |
| Google Gemini ⚠ | openai | 通过 OpenAI 兼容端点 |
| Ollama（本地部署）⚠ | openai | `localhost:11434`，Key 随便填 |
| 自定义（OpenAI 协议） | openai | vLLM / one-api / LiteLLM / 自建网关 |
| 自定义（Anthropic 协议） | anthropic | 任何 Anthropic 兼容层 |

> **⚠ 标记**表示预填地址/模型**未经实测核实**，页面会显示橙色提示。请对照厂商文档确认，或点 🔄 拉取真实模型列表。其余各项均已实际验证可用。

### ⚠️ 火山方舟用户注意

ARK 有两个**计费不同**的产品，务必选对：

| 你的情况 | 选哪项 | Base URL |
|---|---|---|
| 买了 **Coding Plan 包月套餐** | 火山方舟 · 包月套餐 | `/api/plan/v3`（OpenAI）或 `/api/plan/v1`（Anthropic） |
| **按量付费** | 火山方舟 · 豆包 | `/api/v3` |

包月套餐模型固定填 `ark-code-latest`，路由到哪个具体模型在火山控制台选。
**用错地址会产生额外费用。**

---

## 向量数据库

页面「向量库」菜单切换，**切换后需重启后端并重新入库文档**（向量数据不跨库迁移）。

| 类型 | 说明 | 需要额外服务？ |
|---|---|---|
| **Chroma**（默认） | 本地文件持久化到 `./data/chroma_db` | ❌ 开箱即用 |
| **Qdrant** | Rust 实现，生产级 | ✅ `docker compose up -d qdrant` |
| **Milvus** | 企业级；填 `.db` 路径走 **Milvus Lite**（零安装），填 `http://host:19530` 连服务器，也支持 Zilliz Cloud | 视模式而定 |

---

## 智能分词（结构感知切分）

**默认策略**。相比按字数硬切，它沿语义边界切分并保留标题上下文。

以 `samples/sample_knowledge.txt`（595 字）为例：

| | 固定窗口 | 结构感知 |
|---|---|---|
| 片段数 | 2 | **6** |
| 问题 | 四个章节混在一片；另一片从 `Q3` 中间开始，丢了`【常见问题】`上下文 | 每章节独立成片，标题完整保留 |
| 问「保修期」Top-1 得分 | 0.719 | **0.791** |

**能识别的结构**：`【章节】` · Markdown `#`~`######`（含层级） · `第X章` · `Q:/A:` 问答对 · `## Sheet:`（Excel） · `## Page N`（PDF）

编号列表如 `1. 整机保修期为 12 个月。` **不会**被误判成标题。

**在页面上调**：「RAG 设置 → 文本切分」

- **切分策略** — 结构感知 / 固定窗口
- **标题前缀开关** — 长章节被拆时每片带 `[技术规格]` 前缀
- **🔍 预览切分效果** — 选文档或粘贴文本，立刻看到片段数、长度分布、章节归属，**不用真的入库**

---

## 回答策略：严格 RAG 还是允许自主回答

「RAG 设置 → 回答策略」的开关，默认**关闭**。

| | 关闭（默认） | 开启 |
|---|---|---|
| 知识库有相关内容 | 依据资料回答 | 依据资料回答，资料不足时可补全 |
| 知识库**没有**相关内容 | 「抱歉，知识库中没有相关信息」 | 用模型自身知识回答 |
| 可追溯性 | ✅ 每句都能追溯到你的文档 | ❌ 用户分不清哪句来自资料 |
| 适用场景 | 价格、政策、承诺等 | 通用问答、技术咨询 |

实测（问「珠穆朗玛峰的海拔」）：

```
关闭：🚫 抱歉，知识库中没有相关信息，我无法回答。
开启：✅ 珠穆朗玛峰的最新海拔高程为 8848.86米，这是2020年12月中尼共同宣布的…
```

**开启后站内问题不受影响** —— 「有没有404页面模板」照样从知识库回答。

<details>
<summary>为什么需要 relevance_threshold（0.76）</summary>

中文 embedding 的特性：**即使完全无关的内容也有 0.65 左右的分数**。而
`similarity_threshold` 必须保持低值（0.5），否则「登录页」这类短查询会检索不到任何东西。

实测本项目知识库的分数分布：

```
站内问题: 0.813 0.827 0.833 0.836 0.850 0.859 0.905
站外问题: 0.649 0.665 0.680 0.702 0.711
间隔 +0.102  → 分界线取 0.76
```

所以用 `relevance_threshold` 区分「检索到了」和「检索到了答案」。
不同知识库可能需要微调这个值。
</details>

---

## 嵌入到你的网站

### 方式 1：`<script>` 标签（最简单）

```html
<script src="http://localhost:8000/widget/customer-service.js?v=1"></script>
<script>
  CustomerService.init({
    apiUrl: 'http://localhost:8000',
    accent: '#0a66c2',
    position: 'right',      // 'left' | 'right'
    enableUpload: true,
  });
</script>
```

> 客服名称、头像、欢迎语**不用写在这里** —— 组件会自动读取「客服信息」页的配置，
> 改一次对所有已嵌入站点生效。
> `?v=1` 是缓存版本号，更新组件后递增它。

### 方式 2：iframe（完全隔离）

```html
<iframe src="http://localhost:8000/embed?api=http://localhost:8000"
        style="position:fixed;right:20px;bottom:20px;width:400px;height:636px;
               border:0;background:transparent;">
</iframe>
```

> **尺寸要给够、背景要透明**：展开后的面板需要 `400 × 636`
> （面板 360×540 + 按钮位 76 + 边距 20）。给小了面板会被裁掉；
> 不设 `background: transparent` 的话，多余区域会露出 iframe 底色，看起来像一块白板。

`/embed` 支持 `api` · `title` · `accent` · `position` · `autoOpen` · `upload` · `bg` 参数。

### 方式 3：小程序

```xml
<web-view src="https://你的域名/embed?api=https://你的API域名" />
```

记得把域名加入小程序后台的**业务域名**白名单。

### Widget 配置项

| 选项 | 默认 | 说明 |
|---|---|---|
| `apiUrl` | `http://localhost:8000` | 后端地址 |
| `title` / `subtitle` | 读后端配置 | 标题（传了会覆盖后端） |
| `avatar` | 读后端配置 | 头像 URL，加载失败退回首字 |
| `welcome` | 读后端配置 | 首条欢迎语 |
| `accent` | `#0a66c2` | 主题色 |
| `position` | `right` | 浮动按钮位置 |
| `autoOpen` | `false` | 加载后自动展开 |
| `enableUpload` | `true` | 显示文件上传按钮 |
| `useServerConfig` | `true` | 是否从 `/api/config` 拉取客服信息 |
| `sessionId` | `null` | 恢复历史会话 |
| `onReady` | `null` | 初始化完成回调 |

```js
CustomerService.open() / close() / toggle() / sendMessage(text) / destroy()
```

组件内置 **Markdown 渲染**（加粗/列表/标题/代码块/引用）和**链接自动可点击**。

详见 [docs/EMBED_GUIDE.md](docs/EMBED_GUIDE.md)（含 Electron / Tauri / iOS / Android / CSP）。

---

## API 速查

Swagger：**http://localhost:8000/docs** · 详细文档：[docs/API.md](docs/API.md)

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/health` | 健康检查 |
| `GET` | `/api/admin/status` | 安装状态检查（页面横幅用） |
| `POST` | `/api/admin/init` | 一键初始化（幂等） |
| `GET` | `/api/admin/version` | 检测更新（比对 GitHub 最新 Release） |
| `GET` `PUT` | `/api/config` | 读取 / 更新全部配置 |
| `GET` | `/api/config/providers` | 厂商注册表 |
| `POST` | `/api/documents/upload` | 上传文档（multipart） |
| `POST` | `/api/documents/process` | 切分 + 向量化 + 入库（支持续传） |
| `POST` | `/api/documents/split-preview` | 预览切分效果（不入库） |
| `GET` | `/api/documents/list` | 文档列表（含入库进度） |
| `DELETE` | `/api/documents/{id}` | 删除文档及其向量 |
| `GET` | `/api/documents/parsers` | 支持的文件格式 |
| `POST` | `/api/chat` | 一次性问答（JSON） |
| `POST` | `/api/chat/stream` | **流式问答（SSE）** |
| `GET` `POST` | `/api/sessions` | 会话列表 / 创建 |
| `GET` | `/api/sessions/{id}/messages` | 会话历史 |
| `POST` | `/api/sessions/{id}/close` | 关闭会话 |
| `GET` | `/api/models` | 模型 + 向量库总览 |
| `POST` | `/api/models/available` | 拉取厂商真实模型列表 |
| `POST` | `/api/models/test` | 测试对话模型连接 |
| `POST` | `/api/models/test-embedding` | 测试向量模型并探测维度 |
| `GET` | `/api/models/vector-db` | 向量库列表 |

**静态页面**（后端直接提供，无需另起服务器）：

| 路径 | 说明 |
|---|---|
| `/` | 首页（快捷入口） |
| `/admin/` | **管理后台** |
| `/embed` | 独立聊天页（iframe 用），保留查询参数 |
| `/widget/customer-service.js` | 嵌入组件 |
| `/widget/demo/` | 嵌入演示 |
| `/docs` · `/redoc` | Swagger / ReDoc |

**SSE 事件**（`/api/chat/stream`）：

```
event: meta      → 首个事件，{session_id}
event: token     → 增量文本，{text}
event: sources   → 来源列表（含 heading / score / filename）
event: done      → 结束，{ok}
event: error     → 出错，{message}
```

---

## 配置项参考

**页面配置优先于 `.env`** —— 正常使用完全不必碰 `.env`。以下供部署脚本 / CI 参考。

<details>
<summary>展开 .env 全部配置项</summary>

| 分类 | 变量 | 默认 |
|---|---|---|
| 应用 | `APP_ENV` / `APP_DEBUG` / `APP_HOST` / `APP_PORT` | `development` / `true` / `0.0.0.0` / `8000` |
| | `UPLOAD_DIR` / `MAX_UPLOAD_MB` | `./uploads` / `20` |
| | `APP_GITHUB_REPO` / `APP_VERSION` | 空 / `0.1.0`（检测更新用） |
| 数据库 | `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db` |
| Redis | `REDIS_URL` / `REDIS_ENABLED` | 空 / `false` |
| 向量库 | `VECTOR_DB_PROVIDER` | `chroma`（`chroma`\|`qdrant`\|`milvus`） |
| | `VECTOR_DB_HOST` / `_PORT` / `_COLLECTION` | `localhost` / `6333` / `knowledge_base` |
| | `VECTOR_DB_EMBEDDING_DIM` | `1024` |
| | `CHROMA_PERSIST_DIR` | `./data/chroma_db` |
| | `VECTOR_DB_MILVUS_URI` / `_TOKEN` / `_DB_NAME` | `./data/milvus.db` / 空 / 空 |
| LLM | `LLM_PROVIDER` / `_API_KEY` / `_BASE_URL` / `_MODEL` | `deepseek` / 空 / … / `deepseek-chat` |
| | `LLM_TEMPERATURE` / `LLM_MAX_TOKENS` / `API_PROTOCOL` | `0.3` / `2048` / `openai` |
| Embedding | `EMBEDDING_API_KEY` / `_BASE_URL` / `_MODEL` / `_DIM` | 空 / … / `text-embedding-3-small` / `1024` |
| RAG | `RAG_TOP_K` / `RAG_SIMILARITY_THRESHOLD` | `5` / `0.5` |
| | `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` | `500` / `100` |
| | `RAG_CHUNK_STRATEGY` / `RAG_CHUNK_PREFIX_HEADING` | `structure` / `true` |
| | `RAG_ALLOW_MODEL_KNOWLEDGE` | `false` |
| | `RAG_RELEVANCE_THRESHOLD` | `0.76` |
| | `RAG_MAX_CONTEXT_CHARS` | `8000` |
| CORS | `CORS_ORIGINS` | `*` |

</details>

> ⚠️ **`backend/data/app.db` 里存着你在页面填的 API Key**（base64 混淆，等同明文）。
> 已在 `.gitignore` 中排除，**不要提交到公开仓库**。

---

## 常见问题

<details>
<summary><b>启动报「缺少依赖」但我装过了</b></summary>

大概率装到了另一个 Python 环境。错误提示会给出**当前解释器**的完整路径，照那条命令装：

```bash
/你的/venv/bin/python -m pip install -r requirements.txt
# 或让脚本自己搞定
python run.py --install
```

PyCharm 用户注意 Run Configuration 里选的解释器是否就是你装依赖的那个。
</details>

<details>
<summary><b>没有 API Key 能跑吗</b></summary>

能。服务会正常启动，非 LLM 的功能都可用。涉及模型调用的接口会返回明确的
`llm_error` / `embedding_error`，方便先联调。
</details>

<details>
<summary><b>问什么都回「知识库中没有相关信息」</b></summary>

1. 「知识文档」里确认有文档且状态是 **就绪**、分片数 > 0
2. 「RAG 设置」把**相似度阈值**调低试试（默认 0.5）
3. 用「🔍 预览切分效果」看文档是否被合理切分
4. 如果希望资料外的问题也能答，开启「回答策略」里的自主回答开关

知识库确实没有相关内容时，这个回答是**符合预期**的。
</details>

<details>
<summary><b>入库很慢 / 中途失败</b></summary>

部分厂商（实测火山方舟）的 embedding 配额是长周期累计的，跑几百片段就会持续返回 429。

本项目已做**断点续传**：中断后进度保留，再点「入库」从上次位置继续，
已完成的片段不重复消耗配额。大知识库建议用脚本挂后台：

```bash
cd backend
python scripts/ingest_retry.py --cooldown 60
# 或挂后台
nohup python scripts/ingest_retry.py > ingest.log 2>&1 &
```

想快很多的话，换配额宽松的 embedding（如阿里 DashScope 的 `text-embedding-v3`）。
注意换模型后维度会变，需同步改向量库维度并**重新入库全部文档**。
</details>

<details>
<summary><b>改了向量库 / Embedding 模型后检索不对</b></summary>

向量维度必须与模型输出一致，且**换模型后必须重新入库**（旧向量维度不同）。

用「🔌 测试并探测维度」自动读出真实维度，页面会自动同步 `embedding.dim` 与向量库维度。
</details>

<details>
<summary><b>火山方舟报 401</b></summary>

检查是否选对了产品项（包月套餐 vs 按量付费），两者 Base URL 不同：

- 包月套餐：`/api/plan/v3`（OpenAI）或 `/api/plan/v1`（Anthropic）
- 按量付费：`/api/v3`

包月套餐的模型名必须是 `ark-code-latest`。
</details>

<details>
<summary><b>聊天时报 429</b></summary>

已内置自动重试（45 秒预算、指数退避），正常聊天基本不会看到。
若连续高频提问仍触发，说明账号配额已达上限，稍等或换配额更高的模型。
</details>

<details>
<summary><b>SSE 在 Nginx 后面断流</b></summary>

关闭缓冲：

```nginx
location /api/chat/stream {
    proxy_pass http://127.0.0.1:8000;
    proxy_buffering off;
    proxy_cache off;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    chunked_transfer_encoding off;
}
```

后端已设置 `X-Accel-Buffering: no`。
</details>

<details>
<summary><b>改了前端却没变化</b></summary>

后端对 `/admin`、`/widget`、`/embed` 已设置 `Cache-Control: no-store`，
正常刷新即可。若仍有问题，硬刷新：**Mac `Cmd+Shift+R`** / **Windows `Ctrl+Shift+R`**。
</details>

<details>
<summary><b>Python 3.14 装不上某些包</b></summary>

`langchain-text-splitters` 装不上不影响 —— 切分器有内置实现，不依赖它。
其余依赖已在 Python 3.14.5 上验证通过。
</details>

---

## 开发与测试

```bash
# 后端：36 个测试
cd backend
python -m pytest src/tests/ -q

# 前端组件自检：17 项断言，在真实 DOM 里跑完整 SSE 流程
cd frontend/widget
npm install       # 装 jsdom
npm test

# 环境自检
cd backend && python scripts/check_env.py
```

> 组件自检值得一说：`node -c` 只做语法检查，检不出「模板字符串被内部反引号截断」
> 这类会让整个 widget 运行时崩溃的错误。`npm test` 会真正执行渲染路径。

---

## 生产部署

> 完整步骤（Nginx 配置、HTTPS、防火墙、备份、升级、故障排查）见
> **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**。下面是可直接照做的最短路径。

### 部署前的三个关键认识

1. **只有 Nginx 该暴露公网** —— 应用绑 `127.0.0.1:8000`，管理后台没有登录，直接对外等于把 API Key 配置页开放给所有人
2. **SSE 必须在 Nginx 关闭缓冲** —— 否则回答不会逐字出现，而是等全部生成完才一次性蹦出来（最常见的坑）
3. **API Key 存在 `backend/data/app.db`**（base64 混淆，等同明文）—— 已被 `.gitignore` 排除，别提交

### 方案 A：Docker Compose（推荐）

```bash
# 1. 装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER          # 重新登录生效

# 2. 拉代码
cd /opt && git clone https://github.com/vfaner/intelligent-customer-service.git intelligent-customer-service
#   国内服务器可用 Gitee 镜像（更快）：
#   git clone https://gitee.com/super_rgh/intelligent-customer-service.git intelligent-customer-service
cd intelligent-customer-service

# 3. 新建 backend/Dockerfile 和 docker-compose.prod.yml
#    （完整内容见 docs/DEPLOYMENT.md 的「方案 A」一节）

# 4. 配置环境
cp backend/.env.example backend/.env
nano backend/.env
#   必改：APP_ENV=production · APP_SECRET_KEY=<随机生成>
#         DATABASE_URL=mysql+aiomysql://cs_user:密码@mysql:3306/cs_db
#         CORS_ORIGINS=https://你的域名
#   生成 SECRET_KEY：
#   python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 5. 启动
docker compose -f docker-compose.prod.yml up -d --build
curl -fsS http://127.0.0.1:8000/health     # 应返回 {"status":"ok"}
```

### 方案 B：systemd + Nginx

```bash
# 1. 装依赖（Ubuntu/Debian）
sudo apt install -y python3.12 python3.12-venv nginx git

# 2. 建专用用户 + 拉代码
sudo useradd -r -s /bin/false -d /opt/ics csapp
sudo mkdir -p /opt/ics && cd /opt/ics && sudo git clone https://github.com/vfaner/intelligent-customer-service.git .
#   国内服务器可换成 Gitee 镜像：
#   sudo git clone https://gitee.com/super_rgh/intelligent-customer-service.git .
sudo chown -R csapp:csapp /opt/ics

# 3. 装 Python 依赖
cd /opt/ics/backend
sudo -u csapp python3 -m venv .venv
sudo -u csapp .venv/bin/pip install -r requirements.txt
sudo -u csapp cp .env.example .env && sudo nano .env

# 4. 写 /etc/systemd/system/ics.service（见 docs/DEPLOYMENT.md 的完整模板）
#    要点：User=csapp · 只绑 127.0.0.1:8000 · Restart=always · ProtectSystem=strict
sudo systemctl enable --now ics
```

### Nginx（无论哪种方案都必须）

```nginx
server {
    listen 443 ssl http2;
    server_name 你的域名;
    client_max_body_size 25M;

    # ⚠ SSE 流式问答：关闭缓冲，否则回答不逐字出现
    location /api/chat/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
        proxy_read_timeout 300s;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### HTTPS 证书

Widget 嵌入 HTTPS 站点时接口也必须是 HTTPS（浏览器拦截混合内容），基本必选：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名 -d www.你的域名
```

### 保护管理后台（三选一）

管理后台**没有内置登录**，按安全级别从高到低：

| 方式 | 做法 |
|---|---|
| **SSH 端口转发**（推荐） | 不对外开放；`ssh -L 8000:127.0.0.1:8000 user@服务器`，本地打开 `localhost:8000/admin/` |
| **IP 白名单** | Nginx 里 `/admin/` 加 `allow 你的IP; deny all;` |
| **Basic 认证** | `htpasswd` + `auth_basic`，同时保护 `/api/config` `/api/admin` 写接口 |

### 首次上线验证

```bash
# 服务活着
curl -fsS https://你的域名/health

# 模型连通（先在管理后台填好 Key）
curl -sS -X POST https://你的域名/api/models/test -H 'Content-Type: application/json' -d '{}'

# SSE 真的是流式（token 应逐条出现，不是一次性吐出）
curl -N -sS -X POST https://你的域名/api/chat/stream \
     -H 'Content-Type: application/json' -d '{"message":"你好"}'
```

### 安全清单

- [ ] `APP_SECRET_KEY` 换成随机值
- [ ] `APP_ENV=production` 且 `APP_DEBUG=false`（debug 会在报错时泄露栈信息）
- [ ] `CORS_ORIGINS` 限定为实际域名（不要留 `*`）
- [ ] 管理后台已加访问控制（上面三选一）
- [ ] 应用只监听 `127.0.0.1`；数据库/Redis/向量库不映射到公网端口
- [ ] 启用 HTTPS
- [ ] 不用 root 跑应用
- [ ] 给 `/api/chat*` 加 Nginx 限流（防刷爆 LLM 账单）
- [ ] 确认 `.gitignore` 生效：`git check-ignore -v backend/data/app.db`
- [ ] 定期备份 `backend/data/`（脚本见 DEPLOYMENT.md），并**实际验证过能恢复**
- [ ] 注意文档内容可能带 prompt injection

---

## License

MIT
