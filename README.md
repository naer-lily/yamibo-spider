# Yamibo Spider

百合会（bbs.yamibo.com）论坛小说镜像后端，为 LNReader 等阅读器提供 REST API 源。

## 快速开始

### 安装

```bash
git clone <repo-url> && cd yamibo-spider
pip install -e .
playwright install chromium
```

### 登录

```bash
python -m server.yamibo.auth
```

会自动打开 Edge 浏览器，手动登录百合会后 Cookie 保存到 `cookies.json`。

### 配置 AI

```bash
cp .env.example .env
# 编辑 .env 填入你的 API key
```

或直接设环境变量：

```bash
set AI_PROVIDER=deepseek
set AI_MODEL=deepseek-chat
set AI_API_KEY=sk-你的key
```

### 启动

```bash
python -m server.app
# 服务运行在 http://localhost:8000
```

## API

### 源接口（LNReader 协议）

```bash
# 浏览（已收藏列表）
GET /api/v1/source/popular?page=1

# 书籍详情 + 章节目录
GET /api/v1/source/novel/yamibo/{tid}

# 章节正文
GET /api/v1/source/chapter/yamibo/{tid}/{pid}
```

### 书目管理

```bash
# 添加书目（自动 AI 分析）
POST /api/v1/library/add
{"tid": "557701"}

# 查看已收藏
GET /api/v1/library/list
```

### 管理

```bash
# 查看/修改 AI 配置
GET  /api/v1/admin/ai-config
PUT  /api/v1/admin/ai-config
{"provider": "deepseek", "model": "deepseek-chat", "api_key": "sk-xxx"}

# 手动刷新某本书
POST /api/v1/admin/refresh/{tid}
```

## AI 提供商

支持 5 种，通过 `AI_PROVIDER` 环境变量或管理 API 切换：

| 值 | 提供商 |
|---|---|
| `deepseek` | DeepSeek |
| `openai` | OpenAI |
| `google` | Google Gemini |
| `anthropic` | Anthropic Claude |
| `openai_compat` | 任意 OpenAI 兼容端点（需设 `AI_BASE_URL`） |

## 测试

```bash
# 单元测试
pytest tests/ -v

# 端到端集成测试（需要 AI API key）
set AI_API_KEY=sk-xxx && python tests/test_integration.py
```

## 项目结构

```
server/
├── app.py              FastAPI 入口
├── config.py           全局配置
├── domain/             Pydantic 领域模型
├── yamibo/             HTTP 客户端 / 登录 / HTML 解析
├── ai/                 pydantic-ai Agent（工具调用模式）
├── db/                 SQLite 持久化
├── parsing/            三种目录解析策略
├── library/            APScheduler 轮询
├── adapters/           LNReader 协议适配
└── routes/             REST API

plugins/                LNReader TypeScript 插件
tests/                  30 个 pytest 测试
```
