"""
端到端集成测试 v3 — AI 只做元信息+策略，章节由 .t_f 正则提取
"""

import asyncio, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("AI_API_KEY", "sk-efa97965c93448b8b7d005f227c7c919")
os.environ.setdefault("AI_PROVIDER", "deepseek")
os.environ.setdefault("AI_MODEL", "deepseek-chat")

from server.config import AIProviderConfig
from server.yamibo.client import yamibo_client, fetch_first_post, fetch_chapter_content
from server.yamibo.parser import extract_author_uid, extract_posts, extract_pid_links, post_text, clean_post_html
from server.ai.analyzer import analyze_first_post
from server.domain import TocStrategy, BookConfig, Chapter, ChapterPattern
from server.db.database import save_book, load_book_config, update_chapters

TEST_CASES = [
    ("557701", "第X话 pid 目录"),
    ("558885", "幕/场结构"),
    ("566181", "卷+编号【NN】"),
]


async def _test_flow(tid: str, desc: str) -> dict:
    """模拟完整的新书目添加流程"""
    cfg = AIProviderConfig(
        provider=os.environ["AI_PROVIDER"],  # type: ignore[arg-type]
        model=os.environ["AI_MODEL"],
        api_key=os.environ["AI_API_KEY"],
    )

    async with yamibo_client() as client:
        print(f"\n── {desc} (tid={tid}) ──")

        # 1. 抓取
        html = await fetch_first_post(client, tid)
        author_uid = extract_author_uid(html)
        if not author_uid:
            raise ValueError(f"无法提取 author_uid")
        posts = extract_posts(html)
        first_tf = posts[0][1] if posts else html
        print(f"[1] HTML={len(html)}, author_uid={author_uid}")

        # 2. AI 分析（只做元信息+策略）
        meta, strategy, exclude_patterns, title_regex = await analyze_first_post(
            first_tf, tid, author_uid, cfg,
        )
        print(f"[2] AI → 策略={strategy.value}, 标题={meta.cn_title}, 作者={meta.author}")

        # 3. 程序从 .t_f 提取章节
        links = extract_pid_links(first_tf)
        chapters = []
        for i, (t, p) in enumerate(links):
            if any(x in t for x in (exclude_patterns or [])):
                continue
            chapters.append(Chapter(index=i + 1, title=t, pid=p))
        print(f"[3] .t_f 提取 → {len(chapters)} 章")
        for ch in chapters[:5]:
            print(f"    [{ch.index}] {ch.title[:35]:35s} pid={ch.pid}")

        # 4. 保存
        config = BookConfig(
            tid=tid, author_uid=author_uid, meta=meta, chapters=chapters,
            chapter_pattern=ChapterPattern(
                strategy=strategy, exclude_patterns=exclude_patterns or [], title_regex=title_regex,
            ),
        )
        await save_book(config)
        loaded = await load_book_config(tid)
        assert loaded is not None
        assert len(loaded.chapters) == len(chapters)
        print(f"[4] DB 验证: {len(loaded.chapters)} 章 ✓")

        # 5. 增量检测（应无假阳性）
        from server.parsing.pid_links import PidLinksStrategy
        strategy_obj = PidLinksStrategy()
        inc_result = await strategy_obj.parse(
            client, tid, author_uid, config.chapter_pattern,
            cached_chapters=chapters,
        )
        print(f"[5] 增量: +{len(inc_result.new_chapters)} 新章 (应为0)")

        # 6. 正文提取
        if chapters:
            content = await fetch_chapter_content(client, tid, chapters[0].pid)
            if content:
                text = post_text(clean_post_html(content))
                print(f"[6] 正文: {len(text)} 字符 → {text[:60]}...")

        return {
            "tid": tid, "desc": desc,
            "title": meta.cn_title,
            "chapters": len(chapters),
            "fake_increment": len(inc_result.new_chapters),
        }


async def main():
    print("Yamibo Spider 集成测试 v3")
    print(f"AI: {os.environ['AI_PROVIDER']}/{os.environ['AI_MODEL']}")
    print(f"流程: AI(元信息+策略) → 程序(.t_f提取章节) → DB → 增量(0假阳性) → 正文")

    # 清理
    from server.db.database import get_db
    db = await get_db()
    for tid, _ in TEST_CASES:
        await db.execute("DELETE FROM chapters WHERE book_tid=?", (tid,))
        await db.execute("DELETE FROM books WHERE tid=?", (tid,))
    await db.commit(); await db.close()

    results = []
    for tid, desc in TEST_CASES:
        try:
            r = await _test_flow(tid, desc)
            results.append(r)
        except Exception as e:
            print(f"  ❌ {e}")
            import traceback; traceback.print_exc()

    print(f"\n{'='*50}")
    print("汇总")
    for r in results:
        flag = "✓" if r["fake_increment"] == 0 else f"⚠️+{r['fake_increment']}"
        print(f"  {r['title'][:25]:25s} | {r['chapters']:3d}章 | 增量 {flag}")

    Path(__file__).parent.joinpath("integration_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), "utf-8")


if __name__ == "__main__":
    asyncio.run(main())
