"""测试 SQLite 数据库操作"""

import pytest

from server.domain import (
    BookConfig, BookMeta, Chapter, ChapterPattern, TocStrategy,
)

pytestmark = pytest.mark.asyncio

TEST_DB_TID = "999999"


async def _cleanup(tid: str):
    from server.db.database import get_db
    db = await get_db()
    await db.execute("DELETE FROM chapters WHERE book_tid = ?", (tid,))
    await db.execute("DELETE FROM books WHERE tid = ?", (tid,))
    await db.commit()
    await db.close()


async def test_save_and_load_book():
    from server.db.database import save_book, load_book_config

    config = BookConfig(
        tid=TEST_DB_TID,
        author_uid="999999",
        meta=BookMeta(
            cn_title="测试小说", author="测试作者", description="测试简介",
            tags=["校园", "百合"],
        ),
        chapters=[
            Chapter(index=1, title="第1话", pid="999999001"),
            Chapter(index=2, title="第2话", pid="999999002"),
        ],
        chapter_pattern=ChapterPattern(
            strategy=TocStrategy.PID_LINKS, exclude_patterns=["发消息"],
        ),
    )

    await save_book(config)

    loaded = await load_book_config(TEST_DB_TID)
    assert loaded is not None
    assert loaded.meta.cn_title == "测试小说"
    assert loaded.meta.author == "测试作者"
    assert len(loaded.chapters) == 2
    assert loaded.chapters[0].index == 1
    assert loaded.chapter_pattern.strategy == TocStrategy.PID_LINKS

    await _cleanup(TEST_DB_TID)


async def test_load_nonexistent():
    from server.db.database import load_book_config
    assert await load_book_config("nonexistent") is None


async def test_book_exists():
    from server.db.database import save_book, book_exists

    tid = f"{TEST_DB_TID}_exists"
    config = BookConfig(
        tid=tid, author_uid="999999",
        meta=BookMeta(cn_title="T", author="A", description="D"),
        chapters=[Chapter(index=1, title="C1", pid="X")],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.SEQUENTIAL),
    )
    await save_book(config)
    assert await book_exists(tid) is True
    await _cleanup(tid)


async def test_list_books():
    from server.db.database import list_books
    books = await list_books()
    assert isinstance(books, list)


async def test_update_chapters():
    from server.db.database import save_book, load_book_config, update_chapters

    tid = f"{TEST_DB_TID}_update"
    config = BookConfig(
        tid=tid, author_uid="999999",
        meta=BookMeta(cn_title="T", author="A", description="D"),
        chapters=[Chapter(index=1, title="C1", pid="P1")],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.SEQUENTIAL),
    )
    await save_book(config)

    await update_chapters(tid, [Chapter(index=2, title="C2", pid="P2")])
    loaded = await load_book_config(tid)
    assert loaded is not None
    assert len(loaded.chapters) >= 2
    await _cleanup(tid)
