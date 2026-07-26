# Yamibo Spider — AGENTS.md

## 项目概述

百合会（bbs.yamibo.com）论坛小说的镜像爬虫后端，为 LNReader 等阅读器提供 REST API 源。附带管理后台 Web UI。

## 目标论坛

仅覆盖 **轻小说/译文区** (forum-55，日轻翻译)，属于 文學區 子版块。

论坛基于 **Discuz! X3.5**，需登录才能访问正文。

## 论坛结构

### URL 模式

| 用途 | URL |
|---|---|
| 版块列表（第N页） | `forum-55-N.html` |
| 帖子页 | `forum.php?mod=viewthread&tid={tid}` |
| 只看作者（第P页） | `forum.php?mod=viewthread&tid={tid}&page={P}&authorid={uid}` |
| 单楼跳转 | `forum.php?mod=redirect&goto=findpost&ptid={tid}&pid={pid}` |
| 搜索（需searchid） | `search.php?mod=forum&searchid={id}&kw={keyword}` |

### HTML 结构

**帖子列表页** (`forum-55-N.html`):
- 帖子行: `tbody[id^="normalthread_"]`
- 标题: `a.s.xst` (href=`thread-TID-1-1.html`)
- 作者: `cite a`
- 回复/查看: `td.num`

**帖子详情页**（两种变体）:
- `.plhin` 可能是 `<table id="pidXXXXXX">`（redirect 页）或 `<div>` 包含 `<table id="pidXXXXXX">`（直链页），parser 兼容两者
- 正文: `.t_f`
- 页面导航: `.pg` → 最后一个数字链接是总页数
- 作者UID: 从"只看该作者"链接提取 `authorid=(\d+)`

**搜索结果页**:
- 每条结果: `li.pbw[id="tid"]` → `h3 > a[href*="tid="]`
- 链接格式: `forum.php?mod=viewthread&tid=XXX&highlight=...`

### 首楼目录格式（5种）

抓取了多个真实帖子后的总结：

| 策略名 | 模式 | 特征 | 覆盖率 |
|---|---|---|---|
| `pid_links` | `<a href="...pid=41256562">第1话 相遇</a>` | 目录项是可点击pid链接 | ~70% |
| `author_posts` | 文字目录无链接，标题如"第X话 XXX" | 需走authorid模式按标题正则匹配 | ~15% |
| `sequential` | 每楼开头只有"1""2""3"等编号 | 无目录，纯按楼层顺序 | ~10% |
| `act_scene` | 幕/场结构: "序幕/第一幕/第二幕" | pid_links的子类型 | ~3% |
| `no_structure` | 完全无编号无目录 | 退化为sequential | ~2% |

**首楼元信息常见字段**: 作者、标题(CN+JP)、tag/标签、简介、翻译者备注、封面图。

**章节标题常见格式**: `第X话 标题`、`第X章 标题`、`【NN】`、`序幕/第X幕/终幕`。

## 架构设计

```
LNReader App ←→ yamibo.js 插件 ←→ Python FastAPI 后端 ←→ Yamibo 论坛
                 │                       ├── SQLite 数据库
                 │                       ├── AI 解析（pydantic-ai 工具调用）
                 │                       └── Jinja2 管理后台 (/admin)
                 └── HTTP (rest API)
```

### 核心流程：添加书目

```
用户输入 tid → 抓取帖子首页 → 检查 SQLite 缓存
  ├── 缓存命中 → 重抓首楼 .t_f → 比对 pid 做增量检测 → 检测完结信号
  └── 缓存未中 → AI Agent (工具调用模式) 分析首楼 HTML
                    ├── set_meta() → 元信息（含完结状态）
                    ├── set_strategy() → 目录策略
                    └── set_status() → 是否已完结
                  → 程序从首楼 .t_f 正则提取章节列表
                  → 写入 SQLite → 返回
```

**关键设计**: AI 只负责语义层面（元信息提取 + 策略判断 + 完结状态），章节列表由程序从首楼 `.t_f` 中提取。限定 `.t_f` 范围后，pid 链接天然干净，无需 AI 逐章识别。

### 章节更新（刷新）

**不依赖服务端定时轮询**。LNReader App 的"更新书库"功能会逐本调用 `parseNovel`，触发增量检测。检测到新章节时自动关键词匹配判断是否完结。

服务端轮询（APScheduler）作为可选功能，默认关闭（`POLL_ENABLED=0`）。

### AI 配置

- 使用 pydantic-ai 全量包
- 通过工具调用（tool calls）收集结构化结果：`set_meta`、`set_strategy`、`set_status`
- 支持动态配置 provider（openai/deepseek/google/anthropic/openai_compat）、model、api_key
- 可通过 `PUT /api/v1/admin/ai-config` 运行时切换，或通过环境变量 `AI_PROVIDER`、`AI_MODEL`、`AI_API_KEY` 配置

### 解析策略

| 策略 | 首次解析 | 增量更新 |
|---|---|---|
| `pid_links` | AI 识别策略 → 程序从首楼 .t_f 正则提取 pid | 重抓首楼 .t_f → 比对 pid |
| `author_posts` | AI 生成 title_regex → authorid 模式逐楼匹配 | 比对章节标题列表 |
| `sequential` | AI 识别策略 → authorid 模式顺序取楼 | 比对楼层数 |

### 完结检测（三层）

| 层级 | 触发时机 | 方法 |
|---|---|---|
| **初次加书** | AI 分析首楼 | `set_status` tool，判断首楼声明 |
| **增量更新** | LNReader 刷新发现新章节 | 关键词匹配（终章/完结/final 等），自动标记 |
| **手动** | 配置页 `/admin/books/{tid}` | 下拉框切换 + "AI 检测完结" 按钮 |

LNReader 插件通过 `to_source_novel` 的 `status` 字段自动展示 `Completed` / `Ongoing`。

### 繁转简

基于 opencc-python-reimplemented，每本书可单独开关（`t2s_enabled`）。`parseChapter` 返回正文前转换。只在使用时转换，不预存库。

## 前端管理界面

访问 `http://localhost:8000/admin`：

| 页面 | 路径 | 功能 |
|---|---|---|
| 仪表盘 | `/admin` | 书目统计、轮询状态、Cookie状态、LNReader 连接指引 |
| 书目管理 | `/admin/books` | 添加/删除/刷新/搜索已收藏书目 + **论坛搜索**（搜新帖一键添加） |
| 书目配置 | `/admin/books/{tid}` | 编辑元信息、状态切换、繁转简开关、查看章节、AI 检测完结 |
| 系统配置 | `/admin/config` | AI 配置表单、轮询启停/间隔（可选） |
| Cookie | `/admin/cookie` | DevTools 导出 / Playwright 登录 / JSON 粘贴，在线验证 |

## LNReader 插件

### 部署

1. `server/static/yamibo.js` — 手写纯 JS 插件（兼容 LNReader Function() 沙箱）
2. `/static/plugins.min.json` — 动态路由，自动拼接绝对 URL
3. LNReader App 中添加仓库：`http://<server>:8000/static/plugins.min.json`

### 插件架构

```
LNReader App
  ├── yamibo.js (沙箱中运行)
  │     ├── require("@libs/storage") — 插件设置持久化
  │     └── fetch(baseUrl + path) — REST API 调用
  └── Python 后端
        ├── GET /api/v1/source/popular — 已收藏书目（分页 20/页）
        ├── GET /api/v1/source/novel/yamibo/{tid} — 详情+增量检测
        ├── GET /api/v1/source/chapter/yamibo/{tid}/{pid} — 正文（含可选 t2s）
        └── GET /api/v1/source/search?q= — 本地书目搜索
```

### 注意事项

- 插件 manifest URL 必须以 `plugins.min.json` 结尾（LNReader 源码硬编码校验）
- 语言字段必须匹配 LNReader 的 `languagesMapping`：`"中文, 汉语, 漢語"`
- 插件必须是 `exports.default = new Plugin()` 模式，不能用 `module.exports =`

## Cookie 管理

Discuz! X3.5 使用动态前缀命名（如 `EeqY_2132_`），关键认证 Cookie（`_auth`、`_saltkey`）是 **HttpOnly** 的，浏览器 Console JS 拿不到。

### 获取方式

1. **Playwright 登录（推荐）**：`python -m server.yamibo.auth` → 生成 `cookies.json`
2. **浏览器 DevTools Application 面板**：逐个查看/导出
3. **EditThisCookie 扩展**：导出完整 JSON

### 校验逻辑

检查 `_auth` + `_member_login_status=1` 同时存在 → 判定有效。无 `discuz_uid` 固定字段。

## Docker

```bash
docker compose build
docker compose up -d
```

- `cookies.json` 和 `db/` 挂载为 volume
- 不含 playwright（~300MB），Cookie 在宿主机获取
- `POLL_ENABLED=0` 默认关闭轮询
- `requirements-docker.txt` 为运行时最小依赖集

## 项目结构

```
yamibo-spider/
├── AGENTS.md                         # 本文件
├── pyproject.toml                    # 依赖管理
├── .env.example                      # 环境变量模板
├── requirements-docker.txt           # Docker 运行时依赖
├── Dockerfile                        # Docker 镜像构建
├── docker-compose.yml                # 容器编排（不提交 git）
├── .dockerignore
│
├── server/
│   ├── app.py                        # FastAPI 入口（lifespan 模式）
│   ├── config.py                     # 全局配置 + AIProviderConfig
│   ├── domain/__init__.py            # Pydantic 领域模型
│   ├── yamibo/
│   │   ├── client.py                 # httpx 客户端 + Cookie 管理
│   │   ├── auth.py                   # Playwright 手动登录
│   │   ├── parser.py                 # HTML 解析（两种 .plhin 结构）
│   │   └── search.py                 # Discuz! 论坛搜索（formhash + searchid）
│   ├── ai/
│   │   ├── provider.py               # 5 种 provider 动态工厂
│   │   └── analyzer.py              # Agent 工具调用 (set_meta/set_strategy/set_status)
│   ├── db/database.py                # SQLite（books + chapters 表，含自动迁移）
│   ├── parsing/
│   │   ├── __init__.py               # 统一策略注册表 STRATEGIES
│   │   ├── base.py                   # 策略抽象基类
│   │   ├── pid_links.py             # pid_links + 自推导正则增量检测
│   │   ├── author_posts.py          # author_posts
│   │   └── sequential.py            # sequential
│   ├── library/scheduler.py          # APScheduler 可选轮询（默认关闭）
│   ├── adapters/lnreader.py          # LNReader 协议适配（含 status）
│   ├── utils/
│   │   └── t2s.py                    # opencc 繁转简工具
│   ├── templates/
│   │   ├── base.html                 # 管理后台布局
│   │   ├── index.html                # 仪表盘
│   │   ├── books.html                # 书目管理（含论坛搜索）
│   │   ├── book_config.html          # 书目配置页
│   │   ├── config.html               # 系统配置
│   │   └── cookie.html               # Cookie 管理
│   ├── static/
│   │   ├── style.css                 # 管理后台样式
│   │   └── yamibo.js                 # LNReader 插件（手写 JS）
│   └── routes/
│       ├── source.py                 # LNReader 源 API + 增量完结检测
│       ├── library.py                # 书目管理 API
│       └── admin.py                  # 管理 API + 前端页面路由
│
├── plugins/
│   ├── package.json                  # 构建工具依赖
│   ├── build.mjs                     # 同步脚本
│   └── chinese/yamibo.ts            # TypeScript 参考源码
│
└── tests/
    ├── conftest.py                   # 共享 fixture（97 测试）
    ├── test_cookie.py                # Cookie 解析单元测试
    ├── test_search.py                # 搜索结果解析测试
    ├── test_db.py                    # SQLite CRUD 测试（14）
    ├── test_parsing.py               # 策略单元测试（9）
    ├── test_adapters.py              # LNReader 适配测试
    ├── test_routes.py                # API 路由测试（37）
    ├── test_yamibo_client.py         # 客户端 + Cookie 测试
    ├── test_yamibo_parser.py         # HTML 解析测试（15）
    └── test_integration.py           # 端到端集成测试
```

## 数据库

SQLite，含两张表：

```sql
books (tid PK, title, author, author_uid, jp_title, description,
       cover_url, tags JSON, status DEFAULT 'ongoing',
       t2s_enabled INTEGER DEFAULT 0, strategy,
       exclude_patterns JSON, title_regex, created_at, updated_at)

chapters (id PK, book_tid FK, chapter_index, title, pid, volume,
          UNIQUE(book_tid, chapter_index))
```

**自动迁移**：旧表无 `status`/`t2s_enabled` 列时，`get_db()` 自动 `ALTER TABLE ADD COLUMN`。

## 管理 API 全览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/admin/status` | 仪表盘总览 |
| GET/PUT | `/api/v1/admin/ai-config` | AI 配置 |
| GET | `/api/v1/admin/books` | 书目列表（含策略+章节数） |
| GET | `/api/v1/admin/books/{tid}/chapters` | 章节列表 |
| GET/PUT | `/api/v1/admin/books/{tid}/config` | 书目配置 CRUD |
| POST | `/api/v1/admin/books/{tid}/check-completed` | AI 检测完结 |
| DELETE | `/api/v1/admin/books/{tid}` | 删除书目 |
| POST | `/api/v1/admin/refresh/{tid}` | 手动刷新 |
| GET | `/api/v1/admin/cookie/status` | Cookie 状态 |
| POST | `/api/v1/admin/cookie/upload` | Cookie 上传 |
| POST | `/api/v1/admin/cookie/verify` | Cookie 在线验证 |
| GET/PUT/POST | `/api/v1/admin/poll/*` | 轮询管理 |
| GET | `/api/v1/admin/search-forum` | 论坛搜索（管理后台） |
| GET | `/static/plugins.min.json` | LNReader 插件清单（动态） |

## 已知限制

1. **author_posts/sequential 策略未实测**: 译文区绝大多数帖子都有 pid 链接，这两类策略仅在单元测试中验证
2. **LNReader 搜索为本地匹配**: `/api/v1/source/search` 仅搜索已收藏书目标题，论坛搜索在管理后台单独使用

## 实测数据

用 DeepSeek (deepseek-chat) 实测 3 种格式帖子：

| tid | 格式 | 章节提取 | 增量假阳性 | 正文提取 |
|---|---|---|---|---|
| 557701 | 第X话 pid 目录 | 45 | 0 | 3125 字符 |
| 558885 | 幕/场结构 | 5 | 0 | 4168 字符 |
| 566181 | 卷+编号【NN】 | 90 | 0 | 2225 字符 |

## 依赖

```
pydantic-ai                         — AI Agent (全量包)
httpx, beautifulsoup4, lxml         — HTTP + HTML 解析
fastapi, uvicorn, Jinja2            — Web 框架 + 模板
playwright                          — 登录认证（可选）
opencc-python-reimplemented          — 繁转简
apscheduler                          — 可选轮询调度
aiosqlite                            — 异步 SQLite
esbuild                              — 插件构建（可选，现用手写 JS）
```

## 编码规范

- 所有注释使用中文
- 类型注解完整
- Pydantic v2 风格模型
- 异步优先 (async/await)
- pytest 测试（97 个测试，0 失败）
