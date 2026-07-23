"""管理 API + 前端页面路由"""

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from server.config import AIProviderConfig, ServerConfig, COOKIE_PATH, ROOT
from server.db.database import (
    load_book_config, update_chapters, list_books_detailed,
    delete_book, get_chapters, count_books, get_strategy_counts,
    check_cookie_status,
)
from server.yamibo.client import yamibo_client, parse_cookie_string, save_cookies, verify_cookie
from server.parsing import STRATEGIES
from server.library import scheduler

router = APIRouter(tags=["admin"])

templates = Jinja2Templates(directory=str(ROOT / "server" / "templates"))


# ── 请求模型 ──

class CookieInput(BaseModel):
    data: str  # Cookie 字符串或 JSON


class PollConfigInput(BaseModel):
    interval_minutes: int = 30
    enabled: bool = True


# ═══════════════════════════════════════════
#  前端页面路由
# ═══════════════════════════════════════════

@router.get("/admin", response_class=HTMLResponse)
async def admin_index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/admin/books", response_class=HTMLResponse)
async def admin_books(request: Request):
    return templates.TemplateResponse(request, "books.html")


@router.get("/admin/config", response_class=HTMLResponse)
async def admin_config(request: Request):
    return templates.TemplateResponse(request, "config.html")


@router.get("/admin/cookie", response_class=HTMLResponse)
async def admin_cookie_page(request: Request):
    return templates.TemplateResponse(request, "cookie.html")


# ═══════════════════════════════════════════
#  LNReader 插件清单（动态生成，含绝对 URL）
# ═══════════════════════════════════════════

@router.get("/static/plugins.min.json")
async def get_plugin_manifest(request: Request):
    base = str(request.base_url).rstrip("/")
    return [{
        "id": "yamibo",
        "name": "Yamibo (百合会)",
        "site": "https://bbs.yamibo.com",
        "lang": "中文, 汉语, 漢語",
        "version": "1.0.0",
        "url": f"{base}/static/yamibo.js",
        "iconUrl": "https://bbs.yamibo.com/static/image/common/logo.png",
    }]


# ═══════════════════════════════════════════
#  API — 仪表盘状态
# ═══════════════════════════════════════════

@router.get("/api/v1/admin/status")
async def get_status(request: Request):
    cfg: ServerConfig = request.app.state.server_config
    cookie = await check_cookie_status()
    strategy_counts = await get_strategy_counts()

    poll_running = scheduler.is_polling()
    next_run = scheduler.get_next_run()
    last_run = scheduler.get_last_run()

    return {
        "book_count": await count_books(),
        "cookie": {"exists": cookie.exists, "valid": cookie.valid},
        "poll": {
            "running": poll_running,
            "interval_minutes": cfg.poll_interval_minutes,
            "last_run": last_run.isoformat() if last_run else None,
            "next_run": next_run.isoformat() if next_run else None,
        },
        "strategy_counts": strategy_counts,
    }


# ═══════════════════════════════════════════
#  API — AI 配置
# ═══════════════════════════════════════════

@router.put("/api/v1/admin/ai-config")
async def update_ai_config(cfg: AIProviderConfig, request: Request):
    request.app.state.server_config.ai = cfg
    return {"status": "ok", "provider": cfg.provider, "model": cfg.model}


@router.get("/api/v1/admin/ai-config")
async def get_ai_config(request: Request):
    cfg: ServerConfig = request.app.state.server_config
    return {
        "provider": cfg.ai.provider,
        "model": cfg.ai.model,
        "base_url": cfg.ai.base_url or "",
        "api_key_set": bool(cfg.ai.api_key),
    }


# ═══════════════════════════════════════════
#  API — Cookie 管理
# ═══════════════════════════════════════════

@router.get("/api/v1/admin/cookie/status")
async def get_cookie_status():
    cookie = await check_cookie_status()
    return {"exists": cookie.exists, "valid": cookie.valid, "key_cookies": cookie.key_cookies}


@router.post("/api/v1/admin/cookie/verify")
async def verify_cookie_route():
    result = await verify_cookie()
    return result


@router.post("/api/v1/admin/cookie/upload")
async def upload_cookie(data: CookieInput):
    try:
        cookies = parse_cookie_string(data.data)
        if not cookies:
            raise HTTPException(400, "未解析到有效 Cookie，请检查格式")
        save_cookies(cookies)
        cookie = await check_cookie_status()
        return {"status": "ok", "cookie_count": len(cookies), "valid": cookie.valid}
    except json.JSONDecodeError:
        raise HTTPException(400, "JSON 格式错误")
    except Exception as e:
        raise HTTPException(400, f"保存失败: {e}")


# ═══════════════════════════════════════════
#  API — 书目管理
# ═══════════════════════════════════════════

@router.get("/api/v1/admin/books")
async def list_books_admin():
    return await list_books_detailed()


@router.get("/api/v1/admin/books/{tid}/chapters")
async def get_book_chapters(tid: str):
    return await get_chapters(tid)


@router.delete("/api/v1/admin/books/{tid}")
async def remove_book(tid: str):
    deleted = await delete_book(tid)
    if not deleted:
        raise HTTPException(404, "书目未找到")
    return {"status": "deleted", "tid": tid}


@router.post("/api/v1/admin/refresh/{tid}")
async def refresh_book(tid: str):
    config = await load_book_config(tid)
    if not config:
        raise HTTPException(404, "书目未找到")

    strategy = STRATEGIES.get(config.chapter_pattern.strategy)
    if not strategy:
        raise HTTPException(400, "未知策略")

    async with yamibo_client() as client:
        result = await strategy.parse(
            client, tid, config.author_uid,
            config.chapter_pattern,
            cached_chapters=config.chapters,
        )

    if result.new_chapters:
        await update_chapters(tid, result.new_chapters)
        return {"status": "ok", "new_chapters": len(result.new_chapters)}

    return {"status": "ok", "new_chapters": 0}


# ═══════════════════════════════════════════
#  API — 轮询管理
# ═══════════════════════════════════════════

@router.get("/api/v1/admin/poll/status")
async def get_poll_status(request: Request):
    cfg: ServerConfig = request.app.state.server_config
    next_run = scheduler.get_next_run()
    last_run = scheduler.get_last_run()
    running = scheduler.is_polling()

    return {
        "running": running,
        "interval_minutes": cfg.poll_interval_minutes,
        "last_run": last_run.isoformat() if last_run else None,
        "next_run": next_run.isoformat() if next_run else None,
        "active_books": await count_books(),
    }


@router.put("/api/v1/admin/poll/config")
async def update_poll_config(data: PollConfigInput, request: Request):
    cfg: ServerConfig = request.app.state.server_config
    cfg.poll_interval_minutes = data.interval_minutes

    if data.enabled and not scheduler.is_polling():
        if data.interval_minutes > 0:
            scheduler.start_scheduler(data.interval_minutes)
    elif not data.enabled:
        scheduler.stop_scheduler()
    elif data.enabled and scheduler.is_polling():
        scheduler.restart_scheduler(data.interval_minutes)

    return {"status": "ok", "running": scheduler.is_polling(), "interval_minutes": data.interval_minutes}


@router.post("/api/v1/admin/poll/start")
async def start_poll(request: Request):
    cfg: ServerConfig = request.app.state.server_config
    if cfg.poll_interval_minutes <= 0:
        cfg.poll_interval_minutes = 30
    scheduler.start_scheduler(cfg.poll_interval_minutes)
    return {"status": "ok", "running": True}


@router.post("/api/v1/admin/poll/stop")
async def stop_poll():
    scheduler.stop_scheduler()
    return {"status": "ok", "running": False}


@router.post("/api/v1/admin/poll/run-now")
async def run_poll_now():
    from server.library.scheduler import poll_all
    import asyncio
    asyncio.create_task(poll_all())
    return {"status": "ok", "message": "轮询已在后台启动"}
