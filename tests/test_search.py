"""测试搜索功能"""


def test_parse_search_results_empty():
    """空 HTML 应返回空列表"""
    from server.yamibo.search import _parse_search_results
    assert _parse_search_results("") == []
    assert _parse_search_results("<div>nothing</div>") == []


def test_parse_search_results_with_items():
    """搜索结果 HTML 解析"""
    from server.yamibo.search import _parse_search_results

    html = """
    <li class="pbw">
        <a class="xst" href="thread-557701-1-1.html">测试标题</a>
        <cite><a>作者名</a></cite>
    </li>
    """
    items = _parse_search_results(html)
    assert len(items) >= 1
    if items:
        assert items[0]["name"] == "测试标题"
        assert "yamibo/557701" in items[0]["path"]


def test_parse_search_results_no_thread_links():
    """无帖子链接的结果页"""
    from server.yamibo.search import _parse_search_results
    items = _parse_search_results("<li>没有链接</li>")
    assert items == []


def test_parse_total_pages():
    """总页数解析"""
    from server.yamibo.search import _parse_total_pages

    html = '<label><span>1</span>/<span>5</span></label>'
    assert _parse_total_pages(html) == 5

    html2 = '<a href="?page=1">1</a><a href="?page=3">3</a>'
    assert _parse_total_pages(html2) == 3


def test_parse_total_pages_single():
    """单页结果"""
    from server.yamibo.search import _parse_total_pages
    assert _parse_total_pages("<div>no pages</div>") == 1


def test_parse_formhash():
    """formhash 提取（需要实际 HTML 但可以用正则验证）"""
    import re
    html = '<input type="hidden" name="formhash" value="abc123def" />'
    m = re.search(r'<input\s+type="hidden"\s+name="formhash"\s+value="([^"]+)"', html)
    assert m is not None
    assert m.group(1) == "abc123def"


def test_parse_searchid():
    """searchid 提取"""
    import re
    html = 'search.php?mod=forum&searchid=abc123def456&kw=test'
    m = re.search(r'searchid=([a-f0-9]+)', html)
    assert m is not None
    assert m.group(1) == "abc123def456"
