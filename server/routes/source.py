"""LNReader 源 API 路由"""

import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from server.yamibo.client import yamibo_client, fetch_first_post, fetch_chapter_content
from server.yamibo.parser import extract_author_uid, clean_post_html, extract_posts, extract_pid_links
from server.ai.analyzer import analyze_first_post
from server.domain import TocStrategy, BookConfig, Chapter, ChapterPattern, BookMeta
from server.db.database import load_book_config, save_book, list_books, update_chapters
from server.parsing.pid_links import PidLinksStrategy
from server.adapters.lnreader import to_source_novel
from server.config import ServerConfig

import re

COMPLETION_KEYWORDS = [
    "终章", "最终话", "最終話", "最终回", "最終回",
    "尾声", "尾聲", "完结", "完結", "大结局",
    "epilogue", "final", "【完】", "［完］", "[完]",
    "全篇完", "全文完", "已完结", "已完結", "正文完",
]


def _detect_completion_signal(chapter_titles: list[str]) -> bool:
    for title in chapter_titles:
        for kw in COMPLETION_KEYWORDS:
            if kw.lower() in title.lower():
                return True
    return False

router = APIRouter(prefix="/api/v1/source", tags=["source"])


def get_config(request: Request) -> ServerConfig:
    return request.app.state.server_config


@router.get("/popular")
async def popular_novels(page: int = 1):
    items = await list_books()
    per_page = 20
    start = (page - 1) * per_page
    chunk = items[start:start + per_page]
    return [
        {"path": f"yamibo/{item.tid}", "name": item.title, "cover": ""}
        for item in chunk
    ]


@router.get("/search")
async def search_novels(q: str = "", page: int = 1):
    """在已收藏书目中搜索"""
    if not q:
        return []
    items = await list_books()
    q_lower = q.lower()
    matched = [
        item for item in items
        if q_lower in item.title.lower() or q_lower in item.tid
    ]
    per_page = 20
    start = (page - 1) * per_page
    return [
        {"path": f"yamibo/{item.tid}", "name": item.title, "cover": ""}
        for item in matched[start:start + per_page]
    ]


@router.get("/novel/yamibo/{tid}")
async def parse_novel(tid: str, request: Request):
    cfg = get_config(request)

    config = await load_book_config(tid)

    if not config:
        async with yamibo_client() as client:
            try:
                html = await fetch_first_post(client, tid)
            except httpx.HTTPStatusError as e:
                raise HTTPException(404, f"帖子不存在: {e.response.status_code}")

            author_uid = extract_author_uid(html)
            if not author_uid:
                raise HTTPException(400, "无法提取作者UID，请确认帖子可访问")

            # AI 只做元信息 + 策略判断
            first_post = extract_posts(html)
            first_tf = first_post[0][1] if first_post else html
            meta, strategy, exclude_patterns, title_regex, _ = await analyze_first_post(
                first_tf, tid, author_uid, cfg.ai,
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
                tid=tid,
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
    else:
        # 缓存命中：增量检测
        async with yamibo_client() as client:
            strategy = PidLinksStrategy()
            result = await strategy.parse(
                client, tid, config.author_uid,
                config.chapter_pattern,
                cached_chapters=config.chapters,
            )
            if result.new_chapters:
                await update_chapters(tid, result.new_chapters)
                config = await load_book_config(tid)

                # 检测完结信号
                if config and config.meta.status != "completed":
                    new_titles = [c.title for c in result.new_chapters]
                    if _detect_completion_signal(new_titles):
                        from server.db.database import update_book_status
                        await update_book_status(tid, "completed")
                        config = await load_book_config(tid)

    assert config is not None
    return to_source_novel(config, str(request.base_url))


@router.get("/chapter/yamibo/{tid}/{pid}")
async def parse_chapter(tid: str, pid: str):
    async with yamibo_client() as client:
        content = await fetch_chapter_content(client, tid, pid)
        if content is None:
            raise HTTPException(404, f"未找到楼层 pid={pid}")
        html = clean_post_html(content)

        # 繁转简
        config = await load_book_config(tid)
        if config and config.meta.t2s_enabled:
            from server.utils.t2s import t2s
            html = t2s(html)

        return Response(content=html, media_type="text/html")
