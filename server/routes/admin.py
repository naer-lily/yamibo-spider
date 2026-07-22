"""管理 API"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from server.config import AIProviderConfig, ServerConfig
from server.db.database import load_book_config, update_chapters
from server.domain import TocStrategy
from server.parsing.pid_links import PidLinksStrategy
from server.parsing.author_posts import AuthorPostsStrategy
from server.parsing.sequential import SequentialStrategy
from server.yamibo.client import yamibo_client

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

STRATEGIES = {
    TocStrategy.PID_LINKS: PidLinksStrategy(),
    TocStrategy.AUTHOR_POSTS: AuthorPostsStrategy(),
    TocStrategy.SEQUENTIAL: SequentialStrategy(),
}


@router.put("/ai-config")
async def update_ai_config(cfg: AIProviderConfig, request: Request):
    request.app.state.server_config.ai = cfg
    return {"status": "ok", "provider": cfg.provider, "model": cfg.model}


@router.get("/ai-config")
async def get_ai_config(request: Request):
    cfg: ServerConfig = request.app.state.server_config
    return {
        "provider": cfg.ai.provider,
        "model": cfg.ai.model,
        "base_url": cfg.ai.base_url,
        "api_key_set": bool(cfg.ai.api_key),
    }


@router.post("/refresh/{tid}")
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
