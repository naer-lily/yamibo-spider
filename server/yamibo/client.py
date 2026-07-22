"""Yamibo HTTP 客户端 — 纯 JSON Cookie + 请求封装"""

import json
from contextlib import asynccontextmanager

import httpx

from server.config import COOKIE_PATH, YAMIBO_BASE, LOGIN_CHECK_URL


def load_cookies() -> dict[str, str]:
    """加载 cookies.json → {name: value}"""
    if not COOKIE_PATH.exists():
        return {}
    data = json.loads(COOKIE_PATH.read_text("utf-8"))
    return {c["name"]: c["value"] for c in data if c.get("name")}


def save_cookies(cookies: list):  # type: ignore[type-arg]
    """保存 Playwright 格式的 cookies 到 JSON"""
    COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_PATH.write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2),
        "utf-8",
    )


@asynccontextmanager
async def yamibo_client(**kwargs):
    """创建带 Cookie 的 httpx 异步客户端"""
    cookies = load_cookies()
    async with httpx.AsyncClient(
        cookies=cookies,
        base_url=YAMIBO_BASE,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        **kwargs,
    ) as client:
        yield client


async def check_login(client: httpx.AsyncClient) -> bool:
    """检查当前 Cookie 是否已登录"""
    r = await client.get(LOGIN_CHECK_URL)
    return "文學區" in r.text


async def fetch_thread_page(
    client: httpx.AsyncClient,
    tid: str,
    page: int = 1,
    author_uid: str | None = None,
) -> str:
    """抓取帖子页面 HTML"""
    params = {"mod": "viewthread", "tid": tid, "page": page}
    if author_uid:
        params["authorid"] = author_uid
    r = await client.get("/forum.php", params=params)
    r.raise_for_status()
    return r.text


async def fetch_chapter_content(
    client: httpx.AsyncClient,
    tid: str,
    pid: str,
) -> str | None:
    """抓取单个楼层的内容HTML

    通过 pid 跳转链接获取，跟随重定向后从页面中提取匹配的 .plhin 楼层。
    """
    from server.yamibo.parser import extract_posts

    pid_url = f"/forum.php?mod=redirect&goto=findpost&ptid={tid}&pid={pid}"
    r = await client.get(pid_url, follow_redirects=True)
    r.raise_for_status()

    for post_pid, content_html in extract_posts(r.text):
        if post_pid == pid:
            return content_html
    return None


async def fetch_first_post(client: httpx.AsyncClient, tid: str) -> str:
    """抓取帖子首页"""
    return await fetch_thread_page(client, tid, page=1)


def parse_cookie_string(raw: str) -> list[dict]:
    """解析 Cookie 字符串为 JSON 数组

    支持两种输入：
      1. name1=value1; name2=value2（浏览器 DevTools 复制）
      2. [{"name":"x","value":"y"},...]（JSON 数组）
    """
    raw = raw.strip()
    if raw.startswith("["):
        return json.loads(raw)

    cookies = []
    for pair in raw.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, _, value = pair.partition("=")
        cookies.append({"name": name.strip(), "value": value.strip()})
    return cookies


def read_cookie_status() -> dict:
    """读取 Cookie 文件状态"""
    if not COOKIE_PATH.exists():
        return {"exists": False, "valid": False, "cookies": []}
    try:
        data = json.loads(COOKIE_PATH.read_text("utf-8"))
        cookies = {c["name"]: c["value"] for c in data}
        valid = cookies.get("discuz_uid", "0") != "0"
        return {"exists": True, "valid": valid, "cookie_count": len(cookies)}
    except Exception:
        return {"exists": True, "valid": False, "cookie_count": 0}


async def verify_cookie() -> dict:
    """用 Cookie 访问论坛验证有效性"""
    try:
        async with yamibo_client() as client:
            r = await client.get(LOGIN_CHECK_URL)
            logged_in = "文學區" in r.text
            return {"valid": logged_in, "checked": True}
    except Exception as e:
        return {"valid": False, "checked": True, "error": str(e)}
