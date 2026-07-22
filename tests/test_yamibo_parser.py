"""测试 HTML 解析器"""

import re


def test_extract_posts():
    from server.yamibo.parser import extract_posts

    html = """
    <div class="plhin">
      <table id="pid41256562"></table>
      <div class="t_f">这是正文内容</div>
    </div>
    <div class="plhin">
      <table id="pid41256616"></table>
      <div class="t_f">第二章</div>
    </div>
    """
    posts = extract_posts(html)
    assert len(posts) == 2
    assert posts[0] == ("41256562", '<div class="t_f">这是正文内容</div>')
    assert posts[1] == ("41256616", '<div class="t_f">第二章</div>')


def test_extract_posts_empty():
    from server.yamibo.parser import extract_posts

    assert extract_posts("") == []
    assert extract_posts("<div>no posts here</div>") == []


def test_clean_post_html():
    from server.yamibo.parser import clean_post_html

    raw = '<div class="t_f">正文</div>'
    cleaned = clean_post_html(raw)
    assert "正文" in cleaned

    raw_with_pstatus = '<div class="pstatus">编辑提示</div><div class="t_f">正文</div>'
    cleaned = clean_post_html(raw_with_pstatus)
    assert "编辑提示" not in cleaned
    assert "正文" in cleaned


def test_post_text():
    from server.yamibo.parser import post_text

    html = '<div>第1话<br>相遇<br>某个傍晚。</div>'
    text = post_text(html)
    assert "第1话" in text
    assert "相遇" in text


def test_extract_author_uid():
    from server.yamibo.parser import extract_author_uid

    html = '<a href="forum.php?mod=viewthread&tid=1&authorid=410275">只看该作者</a>'
    uid = extract_author_uid(html)
    assert uid == "410275"

    assert extract_author_uid("<div>no link</div>") is None


def test_extract_total_pages():
    from server.yamibo.parser import extract_total_pages

    html = '<div class="pg"><a>1</a><a>2</a><a>3</a><a>下一页</a></div>'
    assert extract_total_pages(html) == 3

    assert extract_total_pages("<div>no pages</div>") == 1


def test_extract_pid_links():
    from server.yamibo.parser import extract_pid_links

    html = """
    <a href="forum.php?mod=redirect&goto=findpost&ptid=557701&pid=41256562">第1话 相遇</a>
    <a href="forum.php?mod=redirect&goto=findpost&ptid=557701&pid=41256616">第2话 启程</a>
    """
    links = extract_pid_links(html)
    assert len(links) == 2
    assert links[0] == ("第1话 相遇", "41256562")
    assert links[1] == ("第2话 启程", "41256616")


def test_extract_pid_links_no_links():
    from server.yamibo.parser import extract_pid_links

    assert extract_pid_links("<div>no links</div>") == []


def test_extract_posts_table_plhin():
    """plhin 作为 table 元素的情况"""
    from server.yamibo.parser import extract_posts

    html = """
    <table class="plhin" id="pid999001">
      <td class="t_f">表格形式的楼层内容</td>
    </table>
    """
    posts = extract_posts(html)
    assert len(posts) == 1
    assert posts[0][0] == "999001"
    assert "表格形式的楼层内容" in posts[0][1]


def test_extract_posts_div_plhin_with_table():
    """plhin 是 div 内含 table id 的情况"""
    from server.yamibo.parser import extract_posts

    html = """
    <div class="plhin">
      <table id="pid999002"></table>
      <div class="t_f">Div包含表格的内容</div>
    </div>
    """
    posts = extract_posts(html)
    assert len(posts) == 1
    assert posts[0][0] == "999002"
    assert "Div包含表格的内容" in posts[0][1]


def test_extract_posts_skips_non_plhin():
    """非 plhin 元素中的 t_f 不应被提取"""
    from server.yamibo.parser import extract_posts

    html = """
    <div>
      <table id="pid999999"></table>
      <div class="t_f">不应被提取</div>
    </div>
    """
    posts = extract_posts(html)
    assert len(posts) == 0


def test_extract_pid_links_empty_title():
    """空标题的 pid 链接应被跳过"""
    from server.yamibo.parser import extract_pid_links

    html = '<a href="?pid=123"></a>'
    links = extract_pid_links(html)
    assert len(links) == 0


def test_extract_pid_links_no_pid_param():
    """没有 pid 参数的链接应被跳过"""
    from server.yamibo.parser import extract_pid_links

    html = '<a href="?thread=123">标题</a>'
    links = extract_pid_links(html)
    assert len(links) == 0


def test_extract_author_uid_no_match():
    """无 authorid 的 HTML"""
    from server.yamibo.parser import extract_author_uid

    html = '<a href="forum.php?mod=viewthread&tid=1">帖子</a>'
    uid = extract_author_uid(html)
    assert uid is None


def test_extract_total_pages_non_digit():
    """页面链接含非数字文本"""
    from server.yamibo.parser import extract_total_pages

    html = '<div class="pg"><a>1</a><a>下一页</a><a>...</a><a>10</a></div>'
    assert extract_total_pages(html) == 10
