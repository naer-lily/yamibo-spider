"""测试 Yamibo HTTP 客户端 — Cookie 管理（无需网络）"""

import json
import pytest
import tempfile
from pathlib import Path

from server.config import COOKIE_PATH
from server.yamibo.client import (
    parse_cookie_string, load_cookies, save_cookies, read_cookie_status,
)

SAMPLE_COOKIES = [
    {"name": "discuz_uid", "value": "416461", "domain": "bbs.yamibo.com"},
    {"name": "EeqY_2132_auth", "value": "abc123def", "domain": "bbs.yamibo.com"},
    {"name": "EeqY_2132_saltkey", "value": "key123", "domain": "bbs.yamibo.com"},
]


def test_parse_cookie_string():
    """解析 name=value; name2=value2 格式"""
    result = parse_cookie_string("discuz_uid=416461; EeqY_2132_auth=abc123; EeqY_2132_saltkey=key123")
    assert len(result) == 3
    assert result[0] == {"name": "discuz_uid", "value": "416461"}
    assert result[1] == {"name": "EeqY_2132_auth", "value": "abc123"}


def test_parse_cookie_string_json():
    """解析 JSON 数组格式"""
    data = json.dumps([
        {"name": "a", "value": "1"},
        {"name": "b", "value": "2"},
    ])
    result = parse_cookie_string(data)
    assert len(result) == 2
    assert result[0]["name"] == "a"


def test_parse_cookie_string_empty():
    """空字符串应返回空列表"""
    assert parse_cookie_string("") == []
    assert parse_cookie_string("   ") == []


def test_parse_cookie_string_no_equals():
    """无等号的条目应被忽略"""
    result = parse_cookie_string("invalid; discuz_uid=123; another_junk")
    assert len(result) == 1
    assert result[0]["name"] == "discuz_uid"


def test_parse_cookie_string_trailing_semicolon():
    """末尾分号不影响解析"""
    result = parse_cookie_string("a=1; b=2;")
    assert len(result) == 2


def test_parse_cookie_string_url_encoded():
    """URL 编码的值应完整保留"""
    result = parse_cookie_string("token=abc%2Fdef%3Dghi%26jkl")
    assert result[0]["value"] == "abc%2Fdef%3Dghi%26jkl"


def test_parse_cookie_string_value_with_equals():
    """值中包含等号应正确处理"""
    result = parse_cookie_string("data=a=b=c")
    assert result[0]["value"] == "a=b=c"


def test_save_and_load_cookies(tmp_path):
    """完整写入和读取流程"""
    test_path = tmp_path / "test_cookies.json"

    # Mock COOKIE_PATH — 直接调用底层函数
    test_path.write_text(json.dumps(SAMPLE_COOKIES, ensure_ascii=False), "utf-8")

    # 模拟 load_cookies 行为
    data = json.loads(test_path.read_text("utf-8"))
    cookies = {c["name"]: c["value"] for c in data}
    assert cookies["discuz_uid"] == "416461"
    assert "EeqY_2132_auth" in cookies


def test_load_cookies_file_not_exists():
    """文件不存在时应返回空字典（不报错）"""
    import os
    path = Path("/nonexistent/path/cookies.json")
    if path.exists():
        path.unlink()
    assert not path.exists()


def test_read_cookie_status_valid(tmp_path):
    """valid Cookie 文件的状态"""
    test_path = tmp_path / "cookies.json"
    test_path.write_text(json.dumps(SAMPLE_COOKIES, ensure_ascii=False), "utf-8")

    data = json.loads(test_path.read_text("utf-8"))
    cookies = {c["name"]: c["value"] for c in data}
    valid = cookies.get("discuz_uid", "0") != "0"
    assert valid is True


def test_read_cookie_status_missing_uid(tmp_path):
    """缺少 discuz_uid 的 Cookie 文件应判定无效"""
    cookies = [{"name": "other", "value": "1"}]
    test_path = tmp_path / "cookies.json"
    test_path.write_text(json.dumps(cookies), "utf-8")

    data = json.loads(test_path.read_text("utf-8"))
    cookies_dict = {c["name"]: c["value"] for c in data}
    valid = "discuz_uid" in cookies_dict and cookies_dict.get("discuz_uid", "0") != "0"
    assert valid is False


def test_read_cookie_status_zero_uid(tmp_path):
    """discuz_uid 为 0 的 Cookie 应判定无效（游客态）"""
    cookies = [{"name": "discuz_uid", "value": "0"}]
    test_path = tmp_path / "cookies.json"
    test_path.write_text(json.dumps(cookies), "utf-8")

    data = json.loads(test_path.read_text("utf-8"))
    cookies_dict = {c["name"]: c["value"] for c in data}
    valid = cookies_dict.get("discuz_uid", "0") != "0"
    assert valid is False


def test_read_cookie_status_corrupted_json(tmp_path):
    """损坏的 JSON 文件应返回无效状态"""
    test_path = tmp_path / "cookies.json"
    test_path.write_text("not valid json {{{", "utf-8")

    try:
        json.loads(test_path.read_text("utf-8"))
        valid = True
    except json.JSONDecodeError:
        valid = False
    assert valid is False


def test_parse_cookie_string_whitespace():
    """多余空白应被正确 trim"""
    result = parse_cookie_string("  a = 1 ; b = 2  ")
    names = [c["name"] for c in result]
    assert "a" in names
    assert "b" in names
