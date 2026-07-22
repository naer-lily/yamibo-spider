"""定时轮询 — 检测章节更新"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from server.yamibo.client import yamibo_client
from server.db.database import list_books, load_book_config, update_chapters
from server.domain import TocStrategy
from server.parsing.pid_links import PidLinksStrategy
from server.parsing.author_posts import AuthorPostsStrategy
from server.parsing.sequential import SequentialStrategy

logger = logging.getLogger(__name__)

STRATEGIES = {
    TocStrategy.PID_LINKS: PidLinksStrategy(),
    TocStrategy.AUTHOR_POSTS: AuthorPostsStrategy(),
    TocStrategy.SEQUENTIAL: SequentialStrategy(),
}


async def poll_book(tid: str):
    config = await load_book_config(tid)
    if not config:
        return

    strategy = STRATEGIES.get(config.chapter_pattern.strategy)
    if not strategy:
        return

    async with yamibo_client() as client:
        result = await strategy.parse(
            client, tid, config.author_uid,
            config.chapter_pattern,
            cached_chapters=config.chapters,
        )

    if result.new_chapters:
        await update_chapters(tid, result.new_chapters)
        logger.info(f"tid={tid} 发现 {len(result.new_chapters)} 个新章节")


async def poll_all():
    library = await list_books()
    logger.info(f"开始轮询 {len(library)} 本书目...")
    for item in library:
        try:
            await poll_book(item.tid)
        except Exception as e:
            logger.error(f"轮询 tid={item.tid} 失败: {e}")


def start_scheduler(interval_minutes: int = 30):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        poll_all, "interval", minutes=interval_minutes,
        id="poll_yamibo", replace_existing=True,
    )
    scheduler.start()
    logger.info(f"轮询已启动，间隔 {interval_minutes} 分钟")
    return scheduler
