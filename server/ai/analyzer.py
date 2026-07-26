"""AI 分析器 — 通过工具调用提取帖子元信息和策略类型

只用 set_meta 和 set_strategy 两个工具。
章节列表由程序从首楼 .t_f 提取，不走 AI。
"""

from dataclasses import dataclass, field
from textwrap import dedent

from pydantic_ai import Agent, RunContext

from server.ai.provider import build_model
from server.config import AIProviderConfig
from server.domain import BookMeta, TocStrategy


@dataclass
class AnalysisState:
    meta: BookMeta | None = None
    strategy: str | None = None
    exclude_patterns: list[str] = field(default_factory=list)
    title_regex: str | None = None
    is_completed: bool | None = None


SYSTEM_PROMPT = dedent("""\
你是一个百合会论坛（bbs.yamibo.com）帖子解析器。
用户会给你一个帖子首页的HTML，你需要调用工具函数提取信息。

调用顺序：
1. set_meta — 记录作品的元信息
2. set_strategy — 判断目录格式类型
3. set_status — 判断作品是否已完结

目录策略说明：
- "pid_links": 首楼正文中有 <a href="...pid=XXXXX">章节名</a> 格式的可点击链接
- "author_posts": 目录是文字列表，没有可点击链接
- "sequential": 没有目录，章节按楼层顺序排列

如果策略是 pid_links，provide exclude_patterns 列出正文中会出现的干扰文本（如"发消息"、"使用道具"）。
如果策略是 author_posts，provide title_regex 用于匹配章节标题（如 r'第(\\d+)话'）。

完结合约判断：如果首楼明确写了"已完结"、"正文已完结"、"完結"、"FIN"等声明，
或标题含有"【完】"标记，则 set completed=True。否则 set completed=False。

完成后简短总结你的发现。
""")


def create_analyzer(cfg: AIProviderConfig):  # type: ignore[return-type]
    """创建用于分析 Yamibo 帖子的 pydantic-ai Agent"""
    model = build_model(cfg)

    agent = Agent(
        model,
        system_prompt=SYSTEM_PROMPT,
        deps_type=AnalysisState,
    )

    @agent.tool
    async def set_meta(
        ctx: RunContext[AnalysisState],
        cn_title: str,
        author: str,
        description: str,
        jp_title: str = "",
        tags: list[str] = [],
        cover_url: str = "",
    ) -> str:
        """记录作品的元信息。

        Args:
            cn_title: 作品中文标题
            author: 作者名（或译者名）
            description: 作品简介/剧情概要
            jp_title: 日文原标题（可选）
            tags: 标签列表，如["校园","百合"]
            cover_url: 封面图片URL（可选）
        """
        ctx.deps.meta = BookMeta(
            cn_title=cn_title,
            jp_title=jp_title,
            author=author,
            description=description,
            cover_url=cover_url or None,
            tags=tags,
        )
        return f"已记录元信息: {cn_title}"

    @agent.tool
    async def set_strategy(
        ctx: RunContext[AnalysisState],
        strategy: str,
        exclude_patterns: list[str] = [],
        title_regex: str = "",
    ) -> str:
        """设置目录解析策略。

        Args:
            strategy: 可选 "pid_links"/"author_posts"/"sequential"
            exclude_patterns: pid_links时排除的文本，如["发消息","使用道具"]
            title_regex: author_posts时匹配章节标题的正则
        """
        ctx.deps.strategy = strategy
        ctx.deps.exclude_patterns = exclude_patterns
        ctx.deps.title_regex = title_regex or None
        return f"已设置策略: {strategy}"

    @agent.tool
    async def set_status(
        ctx: RunContext[AnalysisState],
        completed: bool,
    ) -> str:
        """设置作品完结状态。

        Args:
            completed: True 表示已完结，False 表示连载中
        """
        ctx.deps.is_completed = completed
        return f"已记录完结状态: {'已完结' if completed else '连载中'}"

    return agent


async def analyze_first_post(
    html: str,
    tid: str,
    author_uid: str,
    cfg: AIProviderConfig,
) -> tuple[BookMeta, TocStrategy, list[str], str | None, bool]:
    """分析帖子首页，返回 (元信息, 策略, exclude_patterns, title_regex, is_completed)

    注意：章节列表不由此函数返回，由程序从 .t_f 提取。
    """
    agent = create_analyzer(cfg)
    state = AnalysisState()
    await agent.run(html, deps=state)  # type: ignore[arg-type]

    if not state.meta:
        raise ValueError("AI 未能提取元信息")
    if not state.strategy:
        raise ValueError("AI 未能识别目录策略")

    if state.is_completed:
        state.meta.status = "completed"

    return (
        state.meta,
        TocStrategy(state.strategy),
        state.exclude_patterns,
        state.title_regex,
        state.is_completed or False,
    )
