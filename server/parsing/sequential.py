"""sequential 策略 — 无目录时顺序提取楼层作为章节"""

from server.domain import Chapter, ChapterPattern
from server.parsing.base import ChapterParseResult, ParseStrategy
from server.yamibo.client import fetch_thread_page
from server.yamibo.parser import extract_total_pages, extract_posts


class SequentialStrategy(ParseStrategy):
    """无目录，将所有作者楼层按顺序当作章节"""

    async def parse(
        self,
        client,
        tid: str,
        author_uid: str,
        pattern: ChapterPattern,
        cached_chapters: list[Chapter] | None = None,
    ) -> ChapterParseResult:
        first_page = await fetch_thread_page(client, tid, page=1, author_uid=author_uid)
        total_pages = extract_total_pages(first_page)

        pages = [first_page]
        for p in range(2, total_pages + 1):
            html = await fetch_thread_page(client, tid, page=p, author_uid=author_uid)
            pages.append(html)

        # 收集所有 pid，跳过首楼（目录）
        all_pids: list[str] = []
        for i, page in enumerate(pages):
            for pid, _ in extract_posts(page):
                all_pids.append(pid)

        # 跳过第一个 pid（首楼 = 目录）
        chapter_pids = all_pids[1:] if len(all_pids) > 1 else []

        chapters: list[Chapter] = []
        for idx, pid in enumerate(chapter_pids):
            chapters.append(Chapter(
                index=idx + 1,
                title=f"第{idx + 1}章",
                pid=pid,
            ))

        cached_pids = {c.pid for c in (cached_chapters or [])}
        new_chapters = [c for c in chapters if c.pid not in cached_pids]

        return ChapterParseResult(chapters=chapters, new_chapters=new_chapters)
