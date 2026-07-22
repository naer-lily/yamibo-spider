"""测试解析策略"""

import pytest
from unittest.mock import AsyncMock, patch

from server.domain import Chapter, ChapterPattern, TocStrategy

pytestmark = pytest.mark.asyncio

MOCK_PLHIN = '<table class="plhin" id="pid999001"><td class="t_f">{body}</td></table>'


async def test_pid_links_strategy():
    from server.parsing.pid_links import PidLinksStrategy

    strategy = PidLinksStrategy()
    pattern = ChapterPattern(
        strategy=TocStrategy.PID_LINKS,
        exclude_patterns=["发消息"],
    )

    first_post_body = """
    <a href="...pid=111">第1话</a>
    <a href="...pid=222">第2话</a>
    <a href="...pid=333">发消息</a>
    """
    mock_html = MOCK_PLHIN.format(body=first_post_body)

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = mock_html
    mock_response.raise_for_status = lambda: None
    mock_client.get.return_value = mock_response

    result = await strategy.parse(mock_client, "123", "456", pattern)

    assert len(result.chapters) == 2
    assert result.chapters[0].title == "第1话"
    assert result.chapters[0].pid == "111"


async def test_pid_links_incremental():
    from server.parsing.pid_links import PidLinksStrategy

    strategy = PidLinksStrategy()
    pattern = ChapterPattern(
        strategy=TocStrategy.PID_LINKS,
        exclude_patterns=["发消息"],
    )

    first_post_body = """
    <a href="...pid=111">第1话</a>
    <a href="...pid=222">第2话</a>
    <a href="...pid=333">第3话</a>
    """
    mock_html = MOCK_PLHIN.format(body=first_post_body)

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = mock_html
    mock_response.raise_for_status = lambda: None
    mock_client.get.return_value = mock_response

    cached = [Chapter(index=1, title="第1话", pid="111")]
    result = await strategy.parse(mock_client, "123", "456", pattern, cached_chapters=cached)

    assert len(result.chapters) == 3
    assert len(result.new_chapters) == 2
    assert result.new_chapters[0].title == "第2话"


async def test_pid_links_no_new():
    """增量检测：无新章节时 new_chapters 为空"""
    from server.parsing.pid_links import PidLinksStrategy

    strategy = PidLinksStrategy()
    pattern = ChapterPattern(strategy=TocStrategy.PID_LINKS)

    first_post_body = '<a href="...pid=111">第1话</a>'
    mock_html = MOCK_PLHIN.format(body=first_post_body)

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = mock_html
    mock_response.raise_for_status = lambda: None
    mock_client.get.return_value = mock_response

    cached = [Chapter(index=1, title="第1话", pid="111")]
    result = await strategy.parse(mock_client, "123", "456", pattern, cached_chapters=cached)

    assert len(result.chapters) == 1
    assert len(result.new_chapters) == 0


async def test_pid_links_empty_first_post():
    """首楼无链接时的回退行为"""
    from server.parsing.pid_links import PidLinksStrategy

    strategy = PidLinksStrategy()
    pattern = ChapterPattern(strategy=TocStrategy.PID_LINKS)

    first_post_body = "没有链接的正文"
    mock_html = MOCK_PLHIN.format(body=first_post_body)

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = mock_html
    mock_response.raise_for_status = lambda: None
    mock_client.get.return_value = mock_response

    result = await strategy.parse(mock_client, "123", "456", pattern)
    # pid_links 策略中有无链接时的回退方案
    assert isinstance(result.chapters, list)


async def test_author_posts_strategy_mock():
    """author_posts 策略基本流程"""
    from server.parsing.author_posts import AuthorPostsStrategy

    strategy = AuthorPostsStrategy()
    pattern = ChapterPattern(
        strategy=TocStrategy.AUTHOR_POSTS,
        title_regex=r"第\d+话",
    )

    mock_html = '<table class="plhin" id="pid111"><td class="t_f"><strong>第1话 相遇</strong>正文</td></table>'

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = mock_html
    mock_response.raise_for_status = lambda: None
    mock_client.get.return_value = mock_response

    result = await strategy.parse(mock_client, "123", "456", pattern)
    assert isinstance(result.chapters, list)


async def test_sequential_strategy_mock():
    """sequential 策略基本流程"""
    from server.parsing.sequential import SequentialStrategy

    strategy = SequentialStrategy()
    pattern = ChapterPattern(strategy=TocStrategy.SEQUENTIAL)

    mock_html = (MOCK_PLHIN + MOCK_PLHIN).format(body="正文", body2="正文2") if "{body2}" in MOCK_PLHIN else MOCK_PLHIN.format(body="正文")

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = mock_html
    mock_response.raise_for_status = lambda: None
    mock_client.get.return_value = mock_response

    result = await strategy.parse(mock_client, "123", "456", pattern)
    assert isinstance(result.chapters, list)


def test_strategy_factory():
    from server.parsing.pid_links import PidLinksStrategy
    from server.parsing.author_posts import AuthorPostsStrategy
    from server.parsing.sequential import SequentialStrategy

    assert isinstance(PidLinksStrategy(), PidLinksStrategy)
    assert isinstance(AuthorPostsStrategy(), AuthorPostsStrategy)
    assert isinstance(SequentialStrategy(), SequentialStrategy)

test_strategy_factory = pytest.mark.asyncio(False)(test_strategy_factory)


def test_unified_registry():
    """统一策略注册表包含所有策略"""
    from server.parsing import STRATEGIES
    from server.parsing.pid_links import PidLinksStrategy
    from server.parsing.author_posts import AuthorPostsStrategy
    from server.parsing.sequential import SequentialStrategy

    assert TocStrategy.PID_LINKS in STRATEGIES
    assert TocStrategy.AUTHOR_POSTS in STRATEGIES
    assert TocStrategy.SEQUENTIAL in STRATEGIES
    assert isinstance(STRATEGIES[TocStrategy.PID_LINKS], PidLinksStrategy)
    assert isinstance(STRATEGIES[TocStrategy.AUTHOR_POSTS], AuthorPostsStrategy)
    assert isinstance(STRATEGIES[TocStrategy.SEQUENTIAL], SequentialStrategy)

test_unified_registry = pytest.mark.asyncio(False)(test_unified_registry)
