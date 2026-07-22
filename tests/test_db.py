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


async def test_delete_book():
    """删除书目应同时删除其章节"""
    from server.db.database import save_book, delete_book, load_book_config

    tid = f"{TEST_DB_TID}_delete"
    config = BookConfig(
        tid=tid, author_uid="999999",
        meta=BookMeta(cn_title="待删除", author="A", description="D"),
        chapters=[Chapter(index=1, title="C1", pid="P1")],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.SEQUENTIAL),
    )
    await save_book(config)

    assert await load_book_config(tid) is not None
    deleted = await delete_book(tid)
    assert deleted is True
    assert await load_book_config(tid) is None


async def test_delete_nonexistent_book():
    """删除不存在的书目应返回 False"""
    from server.db.database import delete_book
    deleted = await delete_book("nonexistent_999999")
    assert deleted is False


async def test_list_books_detailed():
    """详细列表应返回策略和章节数"""
    from server.db.database import save_book, list_books_detailed, delete_book

    tid = f"{TEST_DB_TID}_detailed"
    config = BookConfig(
        tid=tid, author_uid="999999",
        meta=BookMeta(cn_title="详细列表测试", author="A", description="D"),
        chapters=[
            Chapter(index=1, title="C1", pid="P1"),
            Chapter(index=2, title="C2", pid="P2"),
            Chapter(index=3, title="C3", pid="P3"),
        ],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.PID_LINKS),
    )
    await save_book(config)

    books = await list_books_detailed()
    assert isinstance(books, list)
    found = [b for b in books if b.tid == tid]
    assert len(found) == 1
    assert found[0].strategy == "pid_links"
    assert found[0].chapter_count == 3
    assert found[0].author == "A"

    await _cleanup(tid)


async def test_get_chapters():
    """获取指定书目的章节列表"""
    from server.db.database import save_book, get_chapters

    tid = f"{TEST_DB_TID}_chapters"
    config = BookConfig(
        tid=tid, author_uid="999999",
        meta=BookMeta(cn_title="章节测试", author="A", description="D"),
        chapters=[
            Chapter(index=1, title="第1话", pid="P1", volume=1),
            Chapter(index=2, title="第2话", pid="P2", volume=2),
        ],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.SEQUENTIAL),
    )
    await save_book(config)

    chapters = await get_chapters(tid)
    assert len(chapters) == 2
    assert chapters[0].title == "第1话"
    assert chapters[0].volume == 1
    assert chapters[1].volume == 2

    await _cleanup(tid)


async def test_get_chapters_empty():
    """没有章节的书目应返回空列表"""
    from server.db.database import save_book, get_chapters

    tid = f"{TEST_DB_TID}_noch"
    config = BookConfig(
        tid=tid, author_uid="999999",
        meta=BookMeta(cn_title="无章节", author="A", description="D"),
        chapters=[],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.SEQUENTIAL),
    )
    await save_book(config)

    chapters = await get_chapters(tid)
    assert chapters == []

    await _cleanup(tid)


async def test_count_books():
    """书目计数"""
    from server.db.database import save_book, count_books, delete_book

    tid = f"{TEST_DB_TID}_count"
    before = await count_books()
    config = BookConfig(
        tid=tid, author_uid="999999",
        meta=BookMeta(cn_title="计数测试", author="A", description="D"),
        chapters=[],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.SEQUENTIAL),
    )
    await save_book(config)
    assert await count_books() == before + 1
    await _cleanup(tid)
    assert await count_books() == before


async def test_get_strategy_counts():
    """策略分布统计"""
    from server.db.database import save_book, get_strategy_counts

    tid_a = f"{TEST_DB_TID}_sc_a"
    tid_b = f"{TEST_DB_TID}_sc_b"

    config_a = BookConfig(
        tid=tid_a, author_uid="999999",
        meta=BookMeta(cn_title="A", author="A", description="D"),
        chapters=[], chapter_pattern=ChapterPattern(strategy=TocStrategy.PID_LINKS),
    )
    config_b = BookConfig(
        tid=tid_b, author_uid="999999",
        meta=BookMeta(cn_title="B", author="B", description="D"),
        chapters=[], chapter_pattern=ChapterPattern(strategy=TocStrategy.SEQUENTIAL),
    )
    await save_book(config_a)
    await save_book(config_b)

    counts = await get_strategy_counts()
    assert isinstance(counts, dict)
    assert "pid_links" in counts
    assert "sequential" in counts

    await _cleanup(tid_a)
    await _cleanup(tid_b)


async def test_check_cookie_status_no_file():
    """无 Cookie 文件时应返回 exists=False"""
    from server.db.database import check_cookie_status
    from server.config import COOKIE_PATH
    import tempfile
    import shutil

    # 临时移走 cookie 文件
    backup = None
    if COOKIE_PATH.exists():
        backup = COOKIE_PATH.read_bytes()
        COOKIE_PATH.unlink()

    try:
        status = await check_cookie_status()
        assert status.exists is False
        assert status.valid is False
        assert status.key_cookies == []
    finally:
        if backup is not None:
            COOKIE_PATH.write_bytes(backup)


async def test_save_book_overwrite():
    """重复保存同一 tid 应覆盖旧数据"""
    from server.db.database import save_book, load_book_config

    tid = f"{TEST_DB_TID}_overwrite"
    config1 = BookConfig(
        tid=tid, author_uid="999999",
        meta=BookMeta(cn_title="旧标题", author="A", description="D"),
        chapters=[Chapter(index=1, title="C1", pid="P1")],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.SEQUENTIAL),
    )
    await save_book(config1)
    loaded1 = await load_book_config(tid)
    assert loaded1.meta.cn_title == "旧标题"

    config2 = BookConfig(
        tid=tid, author_uid="999999",
        meta=BookMeta(cn_title="新标题", author="A", description="D2"),
        chapters=[Chapter(index=1, title="C1A", pid="P1A")],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.PID_LINKS),
    )
    await save_book(config2)
    loaded2 = await load_book_config(tid)
    assert loaded2.meta.cn_title == "新标题"
    assert len(loaded2.chapters) == 1
    assert loaded2.chapters[0].title == "C1A"

    await _cleanup(tid)
