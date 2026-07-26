"""繁转简工具 — 基于 opencc"""

_OPENCC = None


def _get_converter():
    global _OPENCC
    if _OPENCC is None:
        from opencc import OpenCC
        _OPENCC = OpenCC("t2s")
    return _OPENCC


def t2s(text: str) -> str:
    """繁体中文转简体中文"""
    return _get_converter().convert(text)
