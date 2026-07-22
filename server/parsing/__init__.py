"""解析策略 — 统一注册表"""

from server.domain import TocStrategy
from server.parsing.pid_links import PidLinksStrategy
from server.parsing.author_posts import AuthorPostsStrategy
from server.parsing.sequential import SequentialStrategy

STRATEGIES = {
    TocStrategy.PID_LINKS: PidLinksStrategy(),
    TocStrategy.AUTHOR_POSTS: AuthorPostsStrategy(),
    TocStrategy.SEQUENTIAL: SequentialStrategy(),
}
