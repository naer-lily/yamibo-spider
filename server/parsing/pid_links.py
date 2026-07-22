"""pid_links 策略 — 从首楼 .t_f 提取 pid 链接作为目录

限定在首楼正文区（.t_f）内提取，天然过滤论坛 UI 噪声。
"""

from server.domain import Chapter, ChapterPattern
from server.parsing.base import ChapterParseResult, ParseStrategy
from server.yamibo.parser import extract_pid_links, extract_posts
from server.yamibo.client import fetch_first_post


class PidLinksStrategy(ParseStrategy):
    """从首楼 .t_f 的 pid 链接中提取目录

    页码噪声（发消息、评分等论坛按钮）不在 .t_f 内，天然被隔离。
    """

    async def parse(
        self,
        client,
        tid: str,
        author_uid: str,
        pattern: ChapterPattern,
        cached_chapters: list[Chapter] | None = None,
    ) -> ChapterParseResult:
        html = await fetch_first_post(client, tid)
        posts = extract_posts(html)

        if not posts:
            return ChapterParseResult(chapters=[], new_chapters=[])

        # 限定在首楼 .t_f 内提取 pid 链接，噪声天然为 0
        first_tf = posts[0][1]
        raw_links = extract_pid_links(first_tf)

        # 保守的 exclude 过滤（安全网）
        exclude = pattern.exclude_patterns or []

        chapters: list[Chapter] = []
        idx = 0
        for title, p in raw_links:
            if any(x in title for x in exclude):
                continue
            idx += 1
            chapters.append(Chapter(index=idx, title=title, pid=p))

        cached_pids = {c.pid for c in (cached_chapters or [])}
        new_chapters = [c for c in chapters if c.pid not in cached_pids]

        return ChapterParseResult(chapters=chapters, new_chapters=new_chapters)
