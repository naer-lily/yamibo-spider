"""FastAPI 应用入口"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn

from server.config import ServerConfig, ROOT
from server.routes.source import router as source_router
from server.routes.library import router as library_router
from server.routes.admin import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config() -> ServerConfig:
    cfg = ServerConfig()
    cfg.ai.api_key = os.environ.get("AI_API_KEY", "")
    cfg.ai.provider = os.environ.get("AI_PROVIDER", cfg.ai.provider)  # type: ignore[assignment]
    cfg.ai.model = os.environ.get("AI_MODEL", cfg.ai.model)
    cfg.ai.base_url = os.environ.get("AI_BASE_URL") or None
    cfg.poll_interval_minutes = int(os.environ.get("POLL_INTERVAL", "30"))
    cfg.poll_enabled = os.environ.get("POLL_ENABLED", "1").lower() not in ("0", "false", "no")
    return cfg


@asynccontextmanager
async def lifespan(app: FastAPI):
    from server.library.scheduler import start_scheduler
    cfg: ServerConfig = app.state.server_config
    if cfg.poll_enabled and cfg.poll_interval_minutes > 0:
        start_scheduler(cfg.poll_interval_minutes)
    yield


def create_app() -> FastAPI:
    server_config = load_config()

    app = FastAPI(
        title="Yamibo Spider",
        description="百合会论坛小说镜像后端",
        version="2.1.0",
        lifespan=lifespan,
    )

    app.state.server_config = server_config

    app.include_router(source_router)
    app.include_router(library_router)
    app.include_router(admin_router)

    # 前端静态文件
    static_dir = ROOT / "server" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def root():
        return RedirectResponse("/admin")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=True)
