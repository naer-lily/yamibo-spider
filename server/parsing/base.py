"""解析策略基类"""

from abc import ABC, abstractmethod
import httpx

from server.domain import Chapter, ChapterPattern


class ChapterParseResult:
    """策略解析结果"""
    def __init__(
        self,
        chapters: list[Chapter],
        new_chapters: list[Chapter] | None = None,
    ):
        self.chapters = chapters
        self.new_chapters = new_chapters or []


class ParseStrategy(ABC):
    """目录解析策略抽象基类"""

    @abstractmethod
    async def parse(
        self,
        client: httpx.AsyncClient,
        tid: str,
        author_uid: str,
        pattern: ChapterPattern,
        cached_chapters: list[Chapter] | None = None,
    ) -> ChapterParseResult:
        """执行解析，返回章节列表和新增章节"""
        ...
