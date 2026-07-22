"""Discuz! HTML 净化 — 提取楼层、正文、pid、目录"""

import re
from bs4 import BeautifulSoup


def _extract_pid(post) -> str | None:
    """从 .plhin 元素提取 pid"""
    # 情况1: .plhin 自身就是 <table id="pidXXXXXX">
    pid_attr = post.get("id", "")
    if pid_attr and pid_attr.startswith("pid"):
        return pid_attr[3:]

    # 情况2: .plhin 内嵌套 <table id="pidXXXXXX">
    inner = post.select_one("table[id^='pid']")
    if inner:
        return str(inner["id"])[3:]

    # 情况3: .plhin 内任意 table
    inner = post.select_one("table[id]")
    if inner:
        pid = str(inner["id"])
        if pid.startswith("pid"):
            return pid[3:]

    return None


def extract_posts(html: str) -> list[tuple[str, str]]:
    """从帖子页面提取所有楼层 (pid, content_html)"""
    soup = BeautifulSoup(html, "lxml")
    result: list[tuple[str, str]] = []
    for post in soup.select(".plhin"):
        pid = _extract_pid(post)
        if not pid:
            continue
        t_f = post.select_one(".t_f")
        if t_f:
            result.append((pid, str(t_f)))
    return result


def clean_post_html(raw_html: str) -> str:
    """净化单楼 HTML，移除编辑提示等干扰"""
    soup = BeautifulSoup(raw_html, "lxml")
    for pstatus in soup.select(".pstatus"):
        pstatus.decompose()
    for tag in soup(["script", "style"]):
        tag.decompose()
    return str(soup)


def post_text(raw_html: str) -> str:
    """提取楼层纯文本"""
    soup = BeautifulSoup(clean_post_html(raw_html), "lxml")
    return soup.get_text(separator="\n", strip=True)


def extract_author_uid(html: str) -> str | None:
    """从帖子首页提取作者 UID"""
    soup = BeautifulSoup(html, "lxml")
    link = soup.select_one('a[href*="authorid="]')
    if link:
        href = str(link.get("href", ""))
        m = re.search(r"authorid=(\d+)", href)
        if m:
            return m.group(1)
    return None


def extract_total_pages(html: str) -> int:
    """从帖子页面提取总页数"""
    soup = BeautifulSoup(html, "lxml")
    pg = soup.select_one(".pg")
    if not pg:
        return 1
    nums = [int(a.text) for a in pg.select("a") if a.text.strip().isdigit()]
    return max(nums) if nums else 1


def extract_pid_links(html: str) -> list[tuple[str, str]]:
    """从首楼 HTML 提取目录 pid 链接，返回 [(章节标题, pid), ...]"""
    soup = BeautifulSoup(html, "lxml")
    result: list[tuple[str, str]] = []
    for a in soup.select('a[href*="pid="]'):
        title = a.get_text(strip=True)
        if not title:
            continue
        href = str(a.get("href", ""))
        m = re.search(r"pid=(\d+)", href)
        if m:
            result.append((title, m.group(1)))
    return result
