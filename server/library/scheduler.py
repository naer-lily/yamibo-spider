"""定时轮询 — 检测章节更新（单例模式，支持运行时启停）"""

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from server.yamibo.client import yamibo_client
from server.db.database import list_books, load_book_config, update_chapters
from server.parsing import STRATEGIES

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_last_run: datetime | None = None


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


def get_last_run() -> datetime | None:
    return _last_run


async def poll_book(tid: str) -> int:
    """轮询单本书，返回新章节数"""
    config = await load_book_config(tid)
    if not config:
        return 0

    strategy = STRATEGIES.get(config.chapter_pattern.strategy)
    if not strategy:
        return 0

    async with yamibo_client() as client:
        result = await strategy.parse(
            client, tid, config.author_uid,
            config.chapter_pattern,
            cached_chapters=config.chapters,
        )

    if result.new_chapters:
        await update_chapters(tid, result.new_chapters)
        logger.info(f"tid={tid} 发现 {len(result.new_chapters)} 个新章节")

    return len(result.new_chapters)


async def poll_all():
    """轮询所有已收藏书目"""
    global _last_run
    _last_run = datetime.now(timezone.utc)

    library = await list_books()
    logger.info(f"开始轮询 {len(library)} 本书目...")
    total_new = 0
    for item in library:
        try:
            new = await poll_book(item.tid)
            total_new += new
        except Exception as e:
            logger.error(f"轮询 tid={item.tid} 失败: {e}")
    logger.info(f"轮询完成，共 {total_new} 个新章节")


def start_scheduler(interval_minutes: int = 30) -> AsyncIOScheduler:
    """启动定时轮询"""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        poll_all, "interval", minutes=interval_minutes,
        id="poll_yamibo", replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"轮询已启动，间隔 {interval_minutes} 分钟")
    return _scheduler


def stop_scheduler():
    """停止定时轮询"""
    global _scheduler
    if _scheduler and _scheduler.running:
        try:
            _scheduler.remove_job("poll_yamibo")
        except JobLookupError:
            pass
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("轮询已停止")


def restart_scheduler(interval_minutes: int = 30):
    """重启定时轮询（用于更改间隔）"""
    stop_scheduler()
    return start_scheduler(interval_minutes)


def is_polling() -> bool:
    return _scheduler is not None and _scheduler.running


def get_next_run() -> datetime | None:
    """获取下次轮询执行时间"""
    if not _scheduler or not _scheduler.running:
        return None
    try:
        job = _scheduler.get_job("poll_yamibo")
        return job.next_run_time if job else None
    except JobLookupError:
        return None
