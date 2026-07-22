"""测试 LNReader 适配器"""

from server.domain import BookConfig, BookMeta, Chapter, ChapterPattern, TocStrategy


def test_to_source_novel():
    from server.adapters.lnreader import to_source_novel

    config = BookConfig(
        tid="557701",
        author_uid="410275",
        meta=BookMeta(
            cn_title="测试标题",
            author="测试作者",
            description="测试简介",
            tags=["校园", "百合"],
        ),
        chapters=[
            Chapter(index=1, title="第1话 相遇", pid="41256562"),
            Chapter(index=2, title="第2话 启程", pid="41256616"),
        ],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.PID_LINKS),
    )

    result = to_source_novel(config, "http://test")

    assert result["path"] == "yamibo/557701"
    assert result["name"] == "测试标题"
    assert result["author"] == "测试作者"
    assert result["summary"] == "测试简介"
    assert result["genres"] == "校园,百合"
    assert result["status"] == "Ongoing"
    assert len(result["chapters"]) == 2
    assert result["chapters"][0]["path"] == "yamibo/557701/41256562"
    assert result["chapters"][0]["chapterNumber"] == 1


def test_empty_tags():
    from server.adapters.lnreader import to_source_novel

    config = BookConfig(
        tid="1", author_uid="1",
        meta=BookMeta(cn_title="T", author="A", description="D"),
        chapters=[],
        chapter_pattern=ChapterPattern(strategy=TocStrategy.SEQUENTIAL),
    )
    result = to_source_novel(config, "http://test")
    assert result["genres"] == ""
