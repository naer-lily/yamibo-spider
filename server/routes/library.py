"""书目管理 API"""

import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from server.yamibo.client import yamibo_client, fetch_first_post
from server.yamibo.parser import extract_author_uid, extract_posts, extract_pid_links
from server.ai.analyzer import analyze_first_post
from server.domain import TocStrategy, BookConfig, Chapter, ChapterPattern
from server.db.database import load_book_config, save_book, list_books, book_exists
from server.config import ServerConfig

router = APIRouter(prefix="/api/v1/library", tags=["library"])


class AddBookRequest(BaseModel):
    tid: str


@router.post("/add")
async def add_book(req: AddBookRequest, request: Request):
    cfg: ServerConfig = request.app.state.server_config

    if await book_exists(req.tid):
        return {"status": "exists", "tid": req.tid}

    async with yamibo_client() as client:
        try:
            html = await fetch_first_post(client, req.tid)
        except httpx.HTTPStatusError as e:
            raise HTTPException(404, f"帖子不存在: {e.response.status_code}")

        author_uid = extract_author_uid(html)
        if not author_uid:
            raise HTTPException(400, "无法提取作者UID")

        # AI 提取元信息 + 策略
        first_post = extract_posts(html)
        first_tf = first_post[0][1] if first_post else html
        meta, strategy, exclude_patterns, title_regex, _ = await analyze_first_post(
            first_tf, req.tid, author_uid, cfg.ai,
        )

        # 程序提取章节
        if strategy == TocStrategy.PID_LINKS:
            links = extract_pid_links(first_tf)
            chapters = []
            for i, (title, p) in enumerate(links):
                if any(x in title for x in (exclude_patterns or [])):
                    continue
                chapters.append(Chapter(index=i + 1, title=title, pid=p))
        else:
            chapters = []

        config = BookConfig(
            tid=req.tid,
            author_uid=author_uid,
            meta=meta,
            chapters=chapters,
            chapter_pattern=ChapterPattern(
                strategy=strategy,
                exclude_patterns=exclude_patterns or [],
                title_regex=title_regex,
            ),
            created_at=datetime.now().isoformat(),
        )
        await save_book(config)

    return {"status": "ok", "tid": req.tid, "title": config.meta.cn_title}


@router.get("/list")
async def list_all():
    return await list_books()
