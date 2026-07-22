"""LNReader 协议适配 — 将内部 BookConfig 映射为 LNReader Plugin API 格式"""

from server.domain import BookConfig, Chapter


def to_novel_item(config: BookConfig, base_url: str) -> dict:
    """BookConfig → LNReader NovelItem"""
    return {
        "path": f"yamibo/{config.tid}",
        "name": config.meta.cn_title,
        "cover": config.meta.cover_url or "",
    }


def to_source_novel(config: BookConfig, base_url: str) -> dict:
    """BookConfig → LNReader SourceNovel"""
    genres = ",".join(config.meta.tags) if config.meta.tags else ""
    return {
        "path": f"yamibo/{config.tid}",
        "name": config.meta.cn_title,
        "cover": config.meta.cover_url or "",
        "author": config.meta.author,
        "artist": "",
        "summary": config.meta.description,
        "genres": genres,
        "status": "Ongoing",
        "chapters": [
            {
                "name": ch.title,
                "path": f"yamibo/{config.tid}/{ch.pid}",
                "releaseTime": "",
                "chapterNumber": ch.index,
            }
            for ch in config.chapters
        ],
    }


def to_chapter_content(html: str) -> str:
    """章节 HTML 直接返回（LNReader 使用 WebView 渲染）"""
    return html
