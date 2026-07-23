"""Discuz! 搜索 — 限制在译文区（forum-55）内搜索"""

import logging
import re
import httpx

from server.yamibo.client import yamibo_client

logger = logging.getLogger(__name__)

FORUM_ID = "55"


async def _extract_formhash(client: httpx.AsyncClient) -> str | None:
    """从搜索页面提取 formhash（CSRF 令牌）"""
    try:
        r = await client.get("/search.php", params={"mod": "forum"})
        r.raise_for_status()
        m = re.search(r'<input\s+type="hidden"\s+name="formhash"\s+value="([^"]+)"', r.text)
        if m:
            return m.group(1)
        m = re.search(r'formhash=([a-f0-9]+)', r.text)
        return m.group(1) if m else None
    except Exception as e:
        logger.error(f"获取 formhash 失败: {e}")
        return None


async def search_posts(keyword: str, page: int = 1) -> tuple[list[dict], int]:
    """搜索译文区内帖子

    Returns:
        ([] 结果列表, 总页数)
    """
    async with yamibo_client() as client:
        formhash = await _extract_formhash(client)
        if not formhash:
            logger.error("无法获取 formhash，搜索失败")
            return [], 0

        r = await client.post(
            "/search.php",
            params={"mod": "forum"},
            data={
                "formhash": formhash,
                "searchsubmit": "yes",
                "srchtxt": keyword,
                "srchtype": "title",
                "srhfid": FORUM_ID,
            },
            follow_redirects=True,
        )
        r.raise_for_status()

        items = _parse_search_results(r.text)
        total_pages = _parse_total_pages(r.text)

        searchid = _parse_searchid(r.text)
        if page > 1 and searchid:
            items = await _fetch_search_page(client, searchid, keyword, page)

        return items, total_pages


async def _fetch_search_page(client: httpx.AsyncClient, searchid: str, keyword: str, page: int) -> list[dict]:
    """通过 searchid 获取指定页的搜索结果"""
    r = await client.get(
        "/search.php",
        params={
            "mod": "forum",
            "searchid": searchid,
            "kw": keyword,
            "page": page,
        },
    )
    r.raise_for_status()
    return _parse_search_results(r.text)


def _parse_searchid(html: str) -> str | None:
    m = re.search(r'searchid=([a-f0-9]+)', html)
    return m.group(1) if m else None


def _parse_total_pages(html: str) -> int:
    m = re.search(r'<label[^>]*>\s*<span[^>]*>1</span>\s*/\s*<span[^>]*>(\d+)</span>', html)
    if m:
        return int(m.group(1))
    nums = re.findall(r'page=(\d+)', html)
    return max(int(n) for n in nums) if nums else 1


def _parse_search_results(html: str) -> list[dict]:
    """解析搜索结果 HTML 为 NovelItem 列表

    Discuz! 搜索结果中，每条结果是一个 li.pbw，其 h3 内包含链接。
    链接格式有两种：forum.php?mod=viewthread&tid=XXX 或 thread-XXX-1-1.html
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    items = []

    for li in soup.select("li.pbw"):
        link = li.select_one('h3 a, a[href*="tid="], a[href*="thread-"]')
        if not link:
            continue
        title = link.get_text(" ", strip=True)
        href = str(link.get("href", ""))
        tid = _extract_tid(href)
        if not tid or not title:
            continue

        items.append({
            "path": f"yamibo/{tid}",
            "name": title,
            "cover": "",
        })

    return items


def _extract_tid(href: str) -> str | None:
    """从链接中提取帖子 tid，支持两种格式"""
    m = re.search(r"tid=(\d+)", href)
    if m:
        return m.group(1)
    m = re.search(r"thread-(\d+)-", href)
    return m.group(1) if m else None
