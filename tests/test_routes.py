"""测试 API 路由"""

import pytest

pytestmark = pytest.mark.asyncio


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
    assert r.status_code in (400, 404, 500)  # 由 httpx 错误或路由处理


async def test_add_book_missing_tid(app_client):
    r = await app_client.post("/api/v1/library/add", json={})
    assert r.status_code == 422  # validation error
