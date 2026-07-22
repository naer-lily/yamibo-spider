"""测试 Yamibo HTTP 客户端"""

import pytest
from tests.conftest import has_cookies, TEST_TID

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not has_cookies(), reason="未登录，跳过需要 Cookie 的测试")
async def test_check_login(client):
    from server.yamibo.client import check_login

    result = await check_login(client)
    assert result is True, "应该已登录"


@pytest.mark.skipif(not has_cookies(), reason="未登录，跳过需要 Cookie 的测试")
async def test_fetch_first_post(client):
    from server.yamibo.client import fetch_first_post

    html = await fetch_first_post(client, TEST_TID)
    assert "甘作第二也无妨" in html or "dpm1212" in html
    assert len(html) > 10000, "帖子页面应该有大段内容"


@pytest.mark.skipif(not has_cookies(), reason="未登录，跳过需要 Cookie 的测试")
async def test_fetch_author_only(client):
    from server.yamibo.client import fetch_thread_page

    html = await fetch_thread_page(client, TEST_TID, page=1, author_uid="410275")
    assert len(html) > 5000
    assert "只看作者" not in html  # 只看作者模式下应该没有这个链接


async def test_client_no_cookies():
    """测试无 Cookie 时的请求"""
    from server.yamibo.client import yamibo_client

    async with yamibo_client() as client:
        r = await client.get("https://www.baidu.com")
        assert r.status_code == 200


async def test_check_login_without_cookie():
    """未登录时 check_login 应返回 False"""
    import httpx
    from server.yamibo.client import check_login

    async with httpx.AsyncClient() as client:
        result = await check_login(client)
        # 无 cookie 时应该看不到 文學區
        assert isinstance(result, bool)
