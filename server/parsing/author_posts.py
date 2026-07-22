"""author_posts 策略 — 通过只看作者模式 + 标题正则匹配提取章节"""

import re
from server.domain import Chapter, ChapterPattern
from server.parsing.base import ChapterParseResult, ParseStrategy
from server.yamibo.client import fetch_thread_page
from server.yamibo.parser import extract_total_pages, post_text


class AuthorPostsStrategy(ParseStrategy):
    """走 authorid 模式逐页获取所有楼层，按 title_regex 匹配章节"""

    async def parse(
        self,
        client,
        tid: str,
        author_uid: str,
        pattern: ChapterPattern,
        cached_chapters: list[Chapter] | None = None,
    ) -> ChapterParseResult:
        if not pattern.title_regex:
            raise ValueError("author_posts 策略需要 title_regex")

        title_re = re.compile(pattern.title_regex)

        # 获取只看作者的第一页
        first_page = await fetch_thread_page(client, tid, page=1, author_uid=author_uid)
        total_pages = extract_total_pages(first_page)

        # 逐页抓取
        pages = [first_page]
        for p in range(2, total_pages + 1):
            html = await fetch_thread_page(client, tid, page=p, author_uid=author_uid)
            pages.append(html)

        # 匹配章节
        chapters: list[Chapter] = []
        idx = 0
        for page in pages:
            from server.yamibo.parser import extract_posts
            for pid, raw_html in extract_posts(page):
                text = post_text(raw_html)
                m = title_re.search(text)
                if m:
                    idx += 1
                    title = m.group(0).strip()
                    chapters.append(Chapter(index=idx, title=title, pid=pid))

        cached_pids = {c.pid for c in (cached_chapters or [])}
        new_chapters = [c for c in chapters if c.pid not in cached_pids]

        return ChapterParseResult(chapters=chapters, new_chapters=new_chapters)
