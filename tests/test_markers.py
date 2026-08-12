"""生成区/用户区边界测试。

这是全项目最重要的一组测试：一旦 merge 逻辑出错，用户手写的内容就没了。
"""

from __future__ import annotations

import pytest

from itmo.vault.markers import (
    MarkerError,
    compose_note,
    has_user_content,
    merge_frontmatter,
    merge_note,
    render_frontmatter,
    split_frontmatter,
    wrap_generated,
    wrap_mine,
)


def _note(generated: str = "旧的生成内容", mine: str = "") -> str:
    body = "\n\n".join([wrap_generated(generated), wrap_mine("## 我的观点", mine)])
    return compose_note(render_frontmatter({"title": "旧标题", "status": "inbox"}), body)


def test_generated_region_is_replaced():
    merged = merge_note(_note(), {"title": "新标题"}, "全新的生成内容")
    assert "全新的生成内容" in merged
    assert "旧的生成内容" not in merged


def test_user_content_survives_rerun_verbatim():
    handwritten = "我在 RTB 竞价里见过完全相反的情况：\n- 第一点\n- 第二点\n\n还有一段随笔。"
    merged = merge_note(_note(mine=handwritten), {"title": "新标题"}, "新内容")
    assert handwritten in merged


def test_user_content_with_markdown_and_wikilinks_survives():
    handwritten = "参考 [[另一篇笔记]] 和 `code`，见 > [!note] 引用块\n\n| a | b |\n| - | - |"
    merged = merge_note(_note(mine=handwritten), {}, "新内容")
    assert handwritten in merged


def test_content_after_generated_region_survives():
    """用户在生成区之后加的整个章节也要保住。"""
    note = _note() + "\n## 我自己加的章节\n\n随便写的东西\n"
    merged = merge_note(note, {}, "新内容")
    assert "## 我自己加的章节" in merged
    assert "随便写的东西" in merged


def test_missing_markers_refuses_to_write():
    note = compose_note(render_frontmatter({"title": "x"}), "没有任何标记的正文")
    with pytest.raises(MarkerError, match="找不到 itmo 生成区标记"):
        merge_note(note, {}, "新内容")


def test_reversed_markers_refuse_to_write():
    body = "<!-- itmo:generated:end -->\n内容\n<!-- itmo:generated:start -->"
    note = compose_note(render_frontmatter({"title": "x"}), body)
    with pytest.raises(MarkerError, match="顺序颠倒"):
        merge_note(note, {}, "新内容")


def test_duplicated_markers_refuse_to_write():
    body = wrap_generated("a") + "\n" + wrap_generated("b")
    note = compose_note(render_frontmatter({"title": "x"}), body)
    with pytest.raises(MarkerError, match="出现多次"):
        merge_note(note, {}, "新内容")


# --------------------------------------------------------------------------
# frontmatter 分级合并
# --------------------------------------------------------------------------


def test_owned_frontmatter_keys_are_overwritten():
    merged = merge_frontmatter("title: 旧标题\ninterviewee: 旧名字", {"title": "新标题"})
    assert "title: 新标题" in merged
    assert "旧标题" not in merged


def test_write_once_keys_are_not_overwritten():
    """用户把 status 改成 done 之后，重跑不能改回 inbox。"""
    merged = merge_frontmatter("status: done\ntitle: x", {"status": "inbox", "title": "y"})
    assert "status: done" in merged
    assert "status: inbox" not in merged


def test_user_tags_are_preserved():
    merged = merge_frontmatter("tags: [interview, 我自己的标签]", {"tags": ["interview"]})
    assert "我自己的标签" in merged


def test_unknown_user_keys_are_preserved():
    merged = merge_frontmatter("title: x\nmy_custom_field: 我的值", {"title": "y"})
    assert "my_custom_field: 我的值" in merged


def test_multiline_yaml_values_are_preserved_verbatim():
    """用户可能写块状列表，不能被打平或丢弃。"""
    existing = "title: x\nrelated:\n  - 笔记A\n  - 笔记B\nstatus: done"
    merged = merge_frontmatter(existing, {"title": "y"})
    assert "  - 笔记A" in merged
    assert "  - 笔记B" in merged


def test_new_keys_are_appended():
    merged = merge_frontmatter("title: x", {"title": "y", "source_url": "https://e.com"})
    assert "source_url: https://e.com" in merged


def test_missing_frontmatter_is_created():
    assert "title: y" in merge_frontmatter(None, {"title": "y"})


# --------------------------------------------------------------------------
# 其他
# --------------------------------------------------------------------------


def test_split_frontmatter_handles_note_without_frontmatter():
    parts = split_frontmatter("# 标题\n\n正文")
    assert parts.frontmatter is None
    assert parts.body == "# 标题\n\n正文"


def test_split_frontmatter_handles_unclosed_fence():
    """开头有 --- 但没闭合时不能吞掉正文。"""
    parts = split_frontmatter("---\ntitle: x\n\n正文内容")
    assert parts.frontmatter is None
    assert "正文内容" in parts.body


def test_has_user_content_detects_written_and_empty():
    assert has_user_content(_note(mine="我写的"))
    assert not has_user_content(_note(mine=""))
    assert not has_user_content(_note(mine="   \n  "))


def test_frontmatter_values_with_colons_are_quoted():
    rendered = render_frontmatter({"title": "AI: the next thing"})
    assert rendered == 'title: "AI: the next thing"'


def test_frontmatter_renders_lists_and_numbers():
    rendered = render_frontmatter({"tags": ["a", "b"], "speaker_confidence": 0.85})
    assert "tags: [a, b]" in rendered
    assert "speaker_confidence: 0.85" in rendered
