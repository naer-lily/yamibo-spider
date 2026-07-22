"""SQLite 数据库 — 书目、章节、配置持久化"""

import json
import aiosqlite
from pathlib import Path

from server.config import DB_PATH
from server.domain import BookConfig, BookMeta, Chapter, LibraryItem, ChapterPattern, TocStrategy, CookieStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    tid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    author_uid TEXT NOT NULL,
    jp_title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    cover_url TEXT,
    tags TEXT DEFAULT '[]',
    strategy TEXT NOT NULL,
    exclude_patterns TEXT DEFAULT '[]',
    title_regex TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_tid TEXT NOT NULL REFERENCES books(tid),
    chapter_index INTEGER NOT NULL,
    title TEXT NOT NULL,
    pid TEXT NOT NULL,
    volume INTEGER DEFAULT 1,
    UNIQUE(book_tid, chapter_index)
);

CREATE INDEX IF NOT EXISTS idx_chapters_tid ON chapters(book_tid);
"""


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.executescript(SCHEMA)
    await db.commit()
    return db


# ── Books ──

async def book_exists(tid: str) -> bool:
    db = await get_db()
    row = await db.execute("SELECT 1 FROM books WHERE tid = ?", (tid,))
    result = await row.fetchone()
    await db.close()
    return result is not None


async def save_book(config: BookConfig):
    """保存或更新一本书（含章节）"""
    db = await get_db()
    await db.execute("""
        INSERT OR REPLACE INTO books (tid, title, author, author_uid,
            jp_title, description, cover_url, tags,
            strategy, exclude_patterns, title_regex,
            created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        config.tid,
        config.meta.cn_title,
        config.meta.author,
        config.author_uid,
        config.meta.jp_title,
        config.meta.description,
        config.meta.cover_url,
        json.dumps(config.meta.tags, ensure_ascii=False),
        config.chapter_pattern.strategy.value,
        json.dumps(config.chapter_pattern.exclude_patterns, ensure_ascii=False),
        config.chapter_pattern.title_regex,
        config.created_at,
        config.created_at,
    ))

    # 替换章节
    await db.execute("DELETE FROM chapters WHERE book_tid = ?", (config.tid,))
    for ch in config.chapters:
        await db.execute(
            "INSERT OR IGNORE INTO chapters (book_tid, chapter_index, title, pid, volume) VALUES (?, ?, ?, ?, ?)",
            (config.tid, ch.index, ch.title, ch.pid, ch.volume),
        )
    await db.commit()
    await db.close()


async def load_book_config(tid: str) -> BookConfig | None:
    """从数据库加载一本书的完整配置"""
    db = await get_db()
    row = await db.execute("SELECT * FROM books WHERE tid = ?", (tid,))
    book = await row.fetchone()
    if not book:
        await db.close()
        return None

    chapter_rows = await db.execute(
        "SELECT * FROM chapters WHERE book_tid = ? ORDER BY chapter_index", (tid,)
    )
    chapters = [
        Chapter(
            index=ch["chapter_index"],
            title=ch["title"],
            pid=ch["pid"],
            volume=ch["volume"],
        )
        for ch in await chapter_rows.fetchall()
    ]
    await db.close()

    return BookConfig(
        tid=book["tid"],
        author_uid=book["author_uid"],
        meta=BookMeta(
            cn_title=book["title"],
            jp_title=book["jp_title"],
            author=book["author"],
            description=book["description"],
            cover_url=book["cover_url"],
            tags=json.loads(book["tags"]) if book["tags"] else [],
        ),
        chapters=chapters,
        chapter_pattern=ChapterPattern(
            strategy=TocStrategy(book["strategy"]),
            exclude_patterns=json.loads(book["exclude_patterns"]) if book["exclude_patterns"] else [],
            title_regex=book["title_regex"],
        ),
        created_at=book["created_at"],
    )


async def update_chapters(tid: str, chapters: list[Chapter]):
    """增量更新章节（仅追加新的）"""
    db = await get_db()
    for ch in chapters:
        await db.execute(
            "INSERT OR IGNORE INTO chapters (book_tid, chapter_index, title, pid, volume) VALUES (?, ?, ?, ?, ?)",
            (tid, ch.index, ch.title, ch.pid, ch.volume),
        )
    await db.execute(
        "UPDATE books SET updated_at = datetime('now') WHERE tid = ?", (tid,)
    )
    await db.commit()
    await db.close()


async def list_books() -> list[LibraryItem]:
    """列出所有已收藏书目"""
    db = await get_db()
    rows = await db.execute("SELECT tid, title, author, created_at FROM books ORDER BY created_at DESC")
    items = [
        LibraryItem(tid=r["tid"], title=r["title"], author=r["author"], added_at=r["created_at"])
        for r in await rows.fetchall()
    ]
    await db.close()
    return items


async def count_books() -> int:
    db = await get_db()
    row = await db.execute("SELECT COUNT(*) FROM books")
    result = await row.fetchone()
    count = result[0] if result else 0
    await db.close()
    return count


async def delete_book(tid: str) -> bool:
    """删除书目及其所有章节"""
    db = await get_db()
    await db.execute("DELETE FROM chapters WHERE book_tid = ?", (tid,))
    cursor = await db.execute("DELETE FROM books WHERE tid = ?", (tid,))
    await db.commit()
    deleted = cursor.rowcount > 0
    await db.close()
    return deleted


async def get_chapters(tid: str) -> list[Chapter]:
    """获取指定书目的章节列表"""
    db = await get_db()
    rows = await db.execute(
        "SELECT * FROM chapters WHERE book_tid = ? ORDER BY chapter_index", (tid,)
    )
    chapters = [
        Chapter(
            index=ch["chapter_index"],
            title=ch["title"],
            pid=ch["pid"],
            volume=ch["volume"],
        )
        for ch in await rows.fetchall()
    ]
    await db.close()
    return chapters


async def list_books_detailed() -> list[LibraryItem]:
    """列出所有已收藏书目（含策略和章节数）"""
    db = await get_db()
    rows = await db.execute("""
        SELECT b.tid, b.title, b.author, b.strategy, b.created_at,
               (SELECT COUNT(*) FROM chapters WHERE book_tid = b.tid) AS ch_count
        FROM books b ORDER BY b.created_at DESC
    """)
    items = [
        LibraryItem(
            tid=r["tid"], title=r["title"], author=r["author"],
            strategy=r["strategy"], chapter_count=r["ch_count"],
            added_at=r["created_at"],
        )
        for r in await rows.fetchall()
    ]
    await db.close()
    return items


async def get_strategy_counts() -> dict[str, int]:
    """获取各策略的书目数量统计"""
    db = await get_db()
    rows = await db.execute("SELECT strategy, COUNT(*) as cnt FROM books GROUP BY strategy")
    result = {r["strategy"]: r["cnt"] for r in await rows.fetchall()}
    await db.close()
    return result


async def check_cookie_status() -> CookieStatus:
    """异步检测 Cookie 文件是否存在及其关键字段"""
    from server.config import COOKIE_PATH
    import json

    if not COOKIE_PATH.exists():
        return CookieStatus(exists=False, valid=False, key_cookies=[])

    try:
        raw = json.loads(COOKIE_PATH.read_text("utf-8"))
        cookies = {c["name"]: c["value"] for c in raw if c.get("name")}
        key_names = ["discuz_uid", "discuz_pw", "discuz_sid"]
        key_cookies = [n for n in key_names if n in cookies]
        valid = "discuz_uid" in cookies and cookies.get("discuz_uid", "0") != "0"
        return CookieStatus(exists=True, valid=valid, key_cookies=key_cookies)
    except Exception:
        return CookieStatus(exists=True, valid=False, key_cookies=[])
