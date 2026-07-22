"""领域模型 — 映射 Yamibo 论坛的结构化数据"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TocStrategy(str, Enum):
    """目录解析策略"""
    PID_LINKS = "pid_links"
    AUTHOR_POSTS = "author_posts"
    SEQUENTIAL = "sequential"


class BookMeta(BaseModel):
    """AI 从首楼提取的作品元信息"""
    cn_title: str = Field(description="作品中文名")
    jp_title: str = Field(default="", description="作品日文原名")
    author: str = Field(description="作者/译者")
    description: str = Field(description="作品简介")
    cover_url: str | None = Field(default=None, description="封面图片URL")
    tags: list[str] = Field(default_factory=list, description="标签列表")


class Chapter(BaseModel):
    """单个章节"""
    index: int = Field(description="章节序号，从1开始")
    title: str = Field(description="章节标题，如'第1话 相遇'")
    pid: str = Field(description="对应楼层的pid")
    volume: int = Field(default=1, description="所属卷号")


class ChapterPattern(BaseModel):
    """AI 生成的章节提取规则（增量更新时复用）"""
    strategy: TocStrategy
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="pid_links模式下排除非章节链接的文本模式"
    )
    title_regex: str | None = Field(
        default=None,
        description="author_posts模式下匹配章节标题的正则"
    )


class BookConfig(BaseModel):
    """AI 生成的一本书的完整解析配置（缓存于 db/configs/{tid}.json）"""
    tid: str
    author_uid: str
    meta: BookMeta
    chapters: list[Chapter] = Field(default_factory=list)
    chapter_pattern: ChapterPattern
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Post(BaseModel):
    """单个楼层"""
    pid: str
    content_html: str
    content_text: str


class ThreadRef(BaseModel):
    """论坛列表中的帖子条目"""
    tid: str
    title: str
    author: str
    reply_count: int
    view_count: int


class LibraryItem(BaseModel):
    """已收藏书目"""
    tid: str
    title: str
    author: str
    strategy: str = ""
    chapter_count: int = 0
    added_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class PollStatus(BaseModel):
    """轮询状态"""
    running: bool = False
    interval_minutes: int = 30
    last_run: str | None = None
    next_run: str | None = None
    active_books: int = 0


class CookieStatus(BaseModel):
    """Cookie 状态"""
    exists: bool = False
    valid: bool = False
    key_cookies: list[str] = Field(default_factory=list)


class AdminStatus(BaseModel):
    """管理仪表盘总览"""
    book_count: int = 0
    cookie: CookieStatus = Field(default_factory=CookieStatus)
    poll: PollStatus = Field(default_factory=PollStatus)
