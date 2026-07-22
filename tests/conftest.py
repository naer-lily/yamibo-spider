"""测试配置 — 共享 fixture 和工具函数"""

import os
import sys
import json
from pathlib import Path

import pytest
import pytest_asyncio
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("AI_API_KEY", "test-key-not-for-production")
os.environ.setdefault("AI_PROVIDER", "openai")
os.environ.setdefault("AI_MODEL", "gpt-4o-mini")
os.environ.setdefault("POLL_INTERVAL", "0")

from server.config import ROOT, COOKIE_PATH


def has_cookies() -> bool:
    return COOKIE_PATH.exists()


def load_test_cookies() -> dict[str, str]:
    if not COOKIE_PATH.exists():
        return {}
    data = json.loads(COOKIE_PATH.read_text("utf-8"))
    return {c["name"]: c["value"] for c in data}


@pytest_asyncio.fixture
async def client():
    """创建带 Cookie 的 httpx 客户端"""
    cookies = load_test_cookies()
    async with httpx.AsyncClient(
        cookies=cookies,
        base_url="https://bbs.yamibo.com",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    ) as cl:
        yield cl


@pytest_asyncio.fixture
async def app_client():
    """FastAPI TestClient"""
    from server.app import create_app
    from httpx import ASGITransport

    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── 已知的测试数据（公开可访问的帖子）──

TEST_TID = "557701"       # 甘作第二也无妨的我 (日轻翻译，有 pid_links 目录)
TEST_PID = "41256562"     # 第1话 pid
TEST_AUTHOR_UID = "410275"
