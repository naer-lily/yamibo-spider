# Yamibo Spider — AGENTS.md

## 项目概述

百合会（bbs.yamibo.com）论坛小说的镜像爬虫后端，为 LNReader 等阅读器提供 REST API 源。

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
LNReader App ←→ TypeScript Plugin ←→ Python FastAPI 后端 ←→ Yamibo 论坛
                                        ├── SQLite 数据库
                                        ├── AI 解析（pydantic-ai 工具调用）
                                        └── 定时轮询更新
```

### 核心流程：添加书目

```
用户输入 tid → 抓取帖子首页 → 检查 SQLite 缓存
  ├── 缓存命中 → 重抓首楼 .t_f → 比对 pid 做增量检测
  └── 缓存未中 → AI Agent (工具调用模式) 分析首楼 HTML
                    ├── set_meta() → 元信息
                    └── set_strategy() → 目录策略
                  → 程序从首楼 .t_f 正则提取章节列表
                  → 写入 SQLite → 返回
```

**关键设计**: AI 只负责语义层面（元信息提取 + 策略判断），章节列表由程序从首楼 `.t_f` 中提取。限定 `.t_f` 范围后，pid 链接天然干净，无需 AI 逐章识别。

### AI 配置

- 使用 pydantic-ai 全量包
- 通过工具调用（tool calls）收集结构化结果，不使用 JSON Schema 输出
- 支持动态配置 provider（openai/deepseek/google/anthropic/openai_compat）、model、api_key
- 可通过 `PUT /api/v1/admin/ai-config` 运行时切换，或通过环境变量 `AI_PROVIDER`、`AI_MODEL`、`AI_API_KEY` 配置

### 解析策略

| 策略 | 首次解析 | 增量更新 |
|---|---|---|
| `pid_links` | AI 识别策略 → 程序从首楼 .t_f 正则提取 pid | 重抓首楼 .t_f → 比对 pid |
| `author_posts` | AI 生成 title_regex → authorid 模式逐楼匹配 | 比对章节标题列表 |
| `sequential` | AI 识别策略 → authorid 模式顺序取楼 | 比对楼层数 |

### pid_links 增量检测

章节从首楼 `.t_f` 中提取，pid 链接天然在正文区内，论坛 UI 噪声被 DOM 结构隔离。增量只需重抓首楼 `.t_f` → 比对 pid 集合。

## 项目结构

```
yamibo-spider/
├── AGENTS.md                         # 本文件
├── README.md                         # 使用说明
├── pyproject.toml                    # 依赖管理
├── .env.example                      # 环境变量模板
├── cookies.json                      # 纯 JSON 格式 Cookie（httpx 直接读取）
│
├── server/
│   ├── app.py                        # FastAPI 入口（lifespan 模式）
│   ├── config.py                     # 全局配置 + AIProviderConfig
│   ├── domain/__init__.py            # Pydantic 领域模型（BookMeta, Chapter, BookConfig等）
│   ├── yamibo/
│   │   ├── client.py                 # httpx 客户端 + Cookie JSON 管理
│   │   ├── auth.py                   # Playwright 手动登录
│   │   └── parser.py                 # HTML 解析（兼容两种 .plhin 结构）
│   ├── ai/
│   │   ├── provider.py               # 5 种 provider 动态工厂
│   │   └── analyzer.py              # 工具调用 Agent (set_meta/set_strategy)
│   ├── db/database.py                # SQLite（books + chapters 表，aiosqlite）
│   ├── parsing/
│   │   ├── base.py                   # 策略抽象基类
│   │   ├── pid_links.py             # pid_links + 自推导正则增量检测
│   │   ├── author_posts.py          # author_posts（title_regex + authorid）
│   │   └── sequential.py            # sequential（顺序楼层）
│   ├── library/scheduler.py          # APScheduler 定时轮询
│   ├── adapters/lnreader.py          # LNReader 协议格式适配
│   └── routes/
│       ├── source.py                 # LNReader 源 API
│       ├── library.py                # 书目管理 API
│       └── admin.py                  # 管理 API（AI 配置/手动刷新）
│
├── plugins/chinese/yamibo.ts         # LNReader TypeScript 薄插件
│
└── tests/
    ├── conftest.py                   # 共享 fixture
    ├── test_yamibo_client.py         # 客户端 + Cookie 测试（直连 Yamibo）
    ├── test_yamibo_parser.py         # HTML 解析测试
    ├── test_db.py                    # SQLite CRUD 测试
    ├── test_parsing.py               # 策略单元测试
    ├── test_adapters.py              # LNReader 适配测试
    ├── test_routes.py                # API 路由测试
    └── test_integration.py           # 端到端集成测试（DeepSeek 实测）
```

## 数据库

SQLite，含两张表：

```sql
books (tid PK, title, author, author_uid, jp_title, description,
       cover_url, tags JSON, strategy, exclude_patterns JSON,
       title_regex, created_at, updated_at)

chapters (id PK, book_tid FK, chapter_index, title, pid, volume,
          UNIQUE(book_tid, chapter_index))
```

## 已知限制

1. **author_posts/sequential 策略未实测**: 译文区绝大多数帖子都有 pid 链接，这两类策略仅在单元测试中验证。
2. **搜索未实现**: 搜索功能计划后续添加，需处理 Discuz! searchid 生命周期。

## 实测数据

用 DeepSeek (deepseek-chat) 实测 3 种格式帖子：

| tid | 格式 | 章节提取 | 增量假阳性 | 正文提取 |
|---|---|---|---|---|
| 557701 | 第X话 pid 目录 | 45 | 0 | 3125 字符 |
| 558885 | 幕/场结构 | 5 | 0 | 4168 字符 |
| 566181 | 卷+编号【NN】 | 90 | 0 | 2225 字符 |

## 依赖

```
pydantic-ai              — AI Agent (全量包)
httpx, beautifulsoup4    — HTTP + HTML 解析
fastapi, uvicorn         — Web 框架
playwright               — 登录认证
apscheduler              — 轮询调度
aiosqlite                — 异步 SQLite
```

## 编码规范

- 所有注释使用中文
- 类型注解完整
- Pydantic v2 风格模型
- 异步优先 (async/await)
- pytest 测试（30 个测试，0 失败）
