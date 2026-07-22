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


async def test_strategy_factory():
    from server.parsing.pid_links import PidLinksStrategy
    from server.parsing.author_posts import AuthorPostsStrategy
    from server.parsing.sequential import SequentialStrategy

    assert isinstance(PidLinksStrategy(), PidLinksStrategy)
    assert isinstance(AuthorPostsStrategy(), AuthorPostsStrategy)
    assert isinstance(SequentialStrategy(), SequentialStrategy)
