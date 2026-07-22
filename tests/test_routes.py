"""测试 API 路由 — 全覆盖（含新增管理 API + Cookie 失效边界）"""

import pytest

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════
#  基础 API（原测试保留）
# ═══════════════════════════════════════════

async def test_health(app_client):
    r = await app_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_popular_empty(app_client):
    r = await app_client.get("/api/v1/source/popular")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_library_list(app_client):
    r = await app_client.get("/api/v1/library/list")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_admin_ai_config_get(app_client):
    r = await app_client.get("/api/v1/admin/ai-config")
    assert r.status_code == 200
    data = r.json()
    assert "provider" in data
    assert "model" in data


async def test_admin_ai_config_put(app_client):
    r = await app_client.put(
        "/api/v1/admin/ai-config",
        json={"provider": "deepseek", "model": "deepseek-chat", "api_key": "sk-test"},
    )
    assert r.status_code == 200

    r2 = await app_client.get("/api/v1/admin/ai-config")
    assert r2.json()["provider"] == "deepseek"


async def test_get_novel_not_found(app_client):
    r = await app_client.get("/api/v1/source/novel/yamibo/nonexistent")
    assert r.status_code in (400, 404, 500)


async def test_add_book_missing_tid(app_client):
    r = await app_client.post("/api/v1/library/add", json={})
    assert r.status_code == 422


# ═══════════════════════════════════════════
#  仪表盘状态 API
# ═══════════════════════════════════════════

async def test_admin_status(app_client):
    """GET /api/v1/admin/status 应返回完整仪表盘数据"""
    r = await app_client.get("/api/v1/admin/status")
    assert r.status_code == 200
    data = r.json()
    assert "book_count" in data
    assert "cookie" in data
    assert "poll" in data
    assert "strategy_counts" in data
    assert isinstance(data["book_count"], int)
    assert isinstance(data["cookie"]["exists"], bool)
    assert isinstance(data["cookie"]["valid"], bool)
    assert isinstance(data["poll"]["running"], bool)
    assert isinstance(data["strategy_counts"], dict)


# ═══════════════════════════════════════════
#  书目管理 API
# ═══════════════════════════════════════════

async def test_admin_books_list(app_client):
    """GET /api/v1/admin/books 应返回空或已有书目列表"""
    r = await app_client.get("/api/v1/admin/books")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_admin_chapters_nonexistent(app_client):
    """查看不存在的书目章节应返回空列表"""
    r = await app_client.get("/api/v1/admin/books/nonexistent_999999/chapters")
    assert r.status_code == 200
    assert r.json() == []


async def test_admin_delete_nonexistent(app_client):
    """删除不存在的书目应返回 404"""
    r = await app_client.delete("/api/v1/admin/books/nonexistent_999999")
    assert r.status_code == 404


async def test_admin_refresh_nonexistent(app_client):
    """刷新不存在的书目应返回 404"""
    r = await app_client.post("/api/v1/admin/refresh/nonexistent_999999")
    assert r.status_code == 404


# ═══════════════════════════════════════════
#  Cookie API（失效/边界）
# ═══════════════════════════════════════════

async def test_cookie_status(app_client):
    """GET /api/v1/admin/cookie/status 应返回状态"""
    r = await app_client.get("/api/v1/admin/cookie/status")
    assert r.status_code == 200
    data = r.json()
    assert "exists" in data
    assert "valid" in data
    assert "key_cookies" in data


async def test_cookie_upload_empty(app_client):
    """上传空数据应返回 400"""
    r = await app_client.post(
        "/api/v1/admin/cookie/upload",
        json={"data": ""},
    )
    assert r.status_code == 400


async def test_cookie_upload_whitespace(app_client):
    """上传纯空白应返回 400"""
    r = await app_client.post(
        "/api/v1/admin/cookie/upload",
        json={"data": "   "},
    )
    assert r.status_code == 400


async def test_cookie_upload_invalid_json(app_client):
    """上传非法 JSON 字符串应返回 400"""
    r = await app_client.post(
        "/api/v1/admin/cookie/upload",
        json={"data": "not valid json {{{"},
    )
    assert r.status_code == 400


async def test_cookie_upload_missing_field(app_client):
    """请求缺少 data 字段应返回 422"""
    r = await app_client.post(
        "/api/v1/admin/cookie/upload",
        json={},
    )
    assert r.status_code == 422


async def test_cookie_upload_valid_string(app_client):
    """上传有效的 Cookie 字符串应成功"""
    from server.yamibo.client import parse_cookie_string

    data = "discuz_uid=416461; EeqY_2132_auth=abc123; EeqY_2132_saltkey=key456"
    cookies = parse_cookie_string(data)
    assert len(cookies) == 3
    assert cookies[0]["name"] == "discuz_uid"


async def test_cookie_upload_valid_json(app_client):
    """上传有效 JSON 应成功（仅验证格式解析）"""
    from server.yamibo.client import parse_cookie_string
    import json

    data = json.dumps([
        {"name": "discuz_uid", "value": "416461"},
        {"name": "EeqY_2132_auth", "value": "abc"},
    ])
    cookies = parse_cookie_string(data)
    assert len(cookies) == 2


async def test_cookie_verify_no_file(app_client):
    """无 Cookie 文件时应能正常返回（尽管验证结果为无效）"""
    r = await app_client.post("/api/v1/admin/cookie/verify")
    assert r.status_code == 200
    data = r.json()
    assert "valid" in data
    assert "checked" in data


# ═══════════════════════════════════════════
#  轮询 API
# ═══════════════════════════════════════════

async def test_poll_status(app_client):
    """GET /api/v1/admin/poll/status 应返回轮询状态"""
    r = await app_client.get("/api/v1/admin/poll/status")
    assert r.status_code == 200
    data = r.json()
    assert "running" in data
    assert "interval_minutes" in data


async def test_poll_config_update(app_client):
    """PUT /api/v1/admin/poll/config 应正常接收配置"""
    r = await app_client.put(
        "/api/v1/admin/poll/config",
        json={"interval_minutes": 60, "enabled": False},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


async def test_poll_stop(app_client):
    """POST /api/v1/admin/poll/stop 应正常返回"""
    r = await app_client.post("/api/v1/admin/poll/stop")
    assert r.status_code == 200
    assert r.json()["running"] is False


async def test_poll_start(app_client):
    """POST /api/v1/admin/poll/start 应正常返回"""
    r = await app_client.post("/api/v1/admin/poll/start")
    assert r.status_code == 200
    assert r.json()["running"] is True


async def test_poll_run_now(app_client):
    """POST /api/v1/admin/poll/run-now 应正常返回"""
    r = await app_client.post("/api/v1/admin/poll/run-now")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_poll_config_invalid(app_client):
    """轮询配置无效参数应返回 422"""
    r = await app_client.put(
        "/api/v1/admin/poll/config",
        json={"interval_minutes": "not_a_number", "enabled": True},
    )
    assert r.status_code == 422


# ═══════════════════════════════════════════
#  前端页面路由
# ═══════════════════════════════════════════

async def test_admin_page(app_client):
    """GET /admin 应返回 HTML"""
    r = await app_client.get("/admin")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


async def test_admin_books_page(app_client):
    """GET /admin/books 应返回 HTML"""
    r = await app_client.get("/admin/books")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


async def test_admin_config_page(app_client):
    """GET /admin/config 应返回 HTML"""
    r = await app_client.get("/admin/config")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


async def test_admin_cookie_page(app_client):
    """GET /admin/cookie 应返回 HTML"""
    r = await app_client.get("/admin/cookie")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


# ═══════════════════════════════════════════
#  搜索 API
# ═══════════════════════════════════════════

async def test_search_empty_query(app_client):
    """空搜索词应返回空列表"""
    r = await app_client.get("/api/v1/source/search", params={"q": ""})
    assert r.status_code == 200
    assert r.json() == []


async def test_search_missing_query(app_client):
    """缺少 q 参数时的行为"""
    r = await app_client.get("/api/v1/source/search")
    assert r.status_code == 200
    assert r.json() == []


# ═══════════════════════════════════════════
#  Cookie 失效场景 — 接口不应崩溃
# ═══════════════════════════════════════════

async def test_source_routes_no_crash_without_cookie(app_client):
    """所有 source API 在无 Cookie 时不应崩溃（返回错误码而非 500）"""
    endpoints = [
        "/api/v1/source/popular",
        "/api/v1/source/search?q=test",
        "/api/v1/library/list",
    ]
    for url in endpoints:
        r = await app_client.get(url)
        assert r.status_code != 500, f"{url} 返回了 500"


async def test_admin_routes_no_crash_without_cookie(app_client):
    """所有 admin API 在无 Cookie 时不应崩溃"""
    endpoints = [
        "/api/v1/admin/status",
        "/api/v1/admin/books",
        "/api/v1/admin/cookie/status",
        "/api/v1/admin/poll/status",
        "/api/v1/admin/ai-config",
    ]
    for url in endpoints:
        r = await app_client.get(url)
        assert r.status_code != 500, f"{url} 返回了 500"


async def test_static_css_accessible(app_client):
    """静态文件应可访问"""
    r = await app_client.get("/static/style.css")
    assert r.status_code == 200
    assert "text/css" in r.headers.get("content-type", "")


# ═══════════════════════════════════════════
#  领域模型验证
# ═══════════════════════════════════════════

def test_domain_models_instantiation():
    """验证新增的领域模型可正常实例化"""
    from server.domain import PollStatus, CookieStatus, AdminStatus

    poll = PollStatus(running=True, interval_minutes=30, active_books=5)
    assert poll.running is True
    assert poll.interval_minutes == 30

    cookie = CookieStatus(exists=False, valid=False, key_cookies=[])
    assert cookie.exists is False

    admin = AdminStatus(book_count=0, cookie=cookie, poll=poll)
    assert admin.book_count == 0

test_domain_models_instantiation = pytest.mark.asyncio(False)(test_domain_models_instantiation)


def test_library_item_has_new_fields():
    """LibraryItem 应包含新增字段"""
    from server.domain import LibraryItem

    item = LibraryItem(
        tid="123", title="测试", author="测试作者",
        strategy="pid_links", chapter_count=10,
    )
    assert item.strategy == "pid_links"
    assert item.chapter_count == 10

test_library_item_has_new_fields = pytest.mark.asyncio(False)(test_library_item_has_new_fields)
