"""服务端全局配置"""

from pathlib import Path
from pydantic import BaseModel
from typing import Literal


# 项目根目录
ROOT = Path(__file__).resolve().parent.parent

# 数据目录
DB_DIR = ROOT / "db"
DB_PATH = DB_DIR / "yamibo.db"
COOKIE_PATH = ROOT / "cookies.json"

# 论坛常量
YAMIBO_BASE = "https://bbs.yamibo.com"
FORUM_ID = "55"  # 轻小说/译文区
LOGIN_CHECK_URL = "https://bbs.yamibo.com/forum-49-1.html"


class AIProviderConfig(BaseModel):
    """AI 提供商配置（可通过环境变量或 admin API 覆盖）"""
    provider: Literal["openai", "deepseek", "google", "anthropic", "openai_compat"] = "deepseek"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str | None = None  # openai_compat 时必填


class ServerConfig(BaseModel):
    """全局服务配置"""
    ai: AIProviderConfig = AIProviderConfig()
    poll_interval_minutes: int = 30
    poll_enabled: bool = False  # 默认关闭，依赖 LNReader 客户端刷新
