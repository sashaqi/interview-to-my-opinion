"""写入 vault 的端到端测试。"""

from __future__ import annotations

import pytest

from itmo.vault.markers import MINE_END, MINE_START
from itmo.vault.render import timestamped_url
from itmo.vault.writer import VaultWriteError, write_notes


@pytest.fixture
def dirs(tmp_path):
    return tmp_path / "06-Interviews", tmp_path / "06-Interviews" / "Viewpoints"


def _write(analysis, transcript, dirs, **kwargs):
    interview_dir, viewpoint_dir = dirs
    return write_notes(
        analysis,
        transcript,
        interview_dir=interview_dir,
        viewpoint_dir=viewpoint_dir,
        threshold=0.7,
        **kwargs,
    )


def test_creates_main_note_and_viewpoint_notes(analysis, transcript, dirs):
    result = _write(analysis, transcript, dirs)
    assert len(result.created) == 2
    assert not result.updated

    interview_dir, viewpoint_dir = dirs
    main = interview_dir / "2026-08-01 How Teams Get the Bottleneck Wrong.md"
    viewpoint = viewpoint_dir / "Evaluation is the hidden cost nobody budgets for.md"
    assert main.exists() and viewpoint.exists()


def test_main_note_links_to_viewpoint_notes(analysis, transcript, dirs):
    _write(analysis, transcript, dirs)
    text = (dirs[0] / "2026-08-01 How Teams Get the Bottleneck Wrong.md").read_text("utf-8")
    assert "[[Evaluation is the hidden cost nobody budgets for]]" in text
    assert "核心主张" in text
    assert "关键表达" in text
    assert "苏格拉底追问卡" in text


def test_viewpoint_note_backlinks_to_main_note(analysis, transcript, dirs):
    _write(analysis, transcript, dirs)
    text = (dirs[1] / "Evaluation is the hidden cost nobody budgets for.md").read_text("utf-8")
    # frontmatter 中的 wikilink 必须带引号，否则 Obsidian 解析不了
    assert 'source: "[[2026-08-01 How Teams Get the Bottleneck Wrong]]"' in text
    assert "30 秒复述" in text
    assert "2 分钟复述" in text
    assert "反方视角" in text


def test_rerun_preserves_handwritten_content(analysis, transcript, dirs):
    """产品的核心安全保证：重跑不能覆盖用户写的东西。"""
    _write(analysis, transcript, dirs)
    main_path = dirs[0] / "2026-08-01 How Teams Get the Bottleneck Wrong.md"

    handwritten = "我在 RTB 竞价场景里见过完全相反的情况，评估反而是最便宜的一环。"
    original = main_path.read_text("utf-8")
    main_path.write_text(
        original.replace(MINE_START, f"{MINE_START}\n{handwritten}"), encoding="utf-8"
    )

    # 改掉分析内容后重跑
    analysis["meta"]["thesis_en"] = "A completely different thesis about something else."
    result = _write(analysis, transcript, dirs)

    updated = main_path.read_text("utf-8")
    assert handwritten in updated
    assert "A completely different thesis" in updated
    assert main_path in result.preserved
    assert main_path in result.updated


def test_rerun_preserves_user_edited_frontmatter_status(analysis, transcript, dirs):
    _write(analysis, transcript, dirs)
    main_path = dirs[0] / "2026-08-01 How Teams Get the Bottleneck Wrong.md"
    main_path.write_text(
        main_path.read_text("utf-8").replace("status: inbox", "status: done"), encoding="utf-8"
    )

    _write(analysis, transcript, dirs)
    assert "status: done" in main_path.read_text("utf-8")


def test_corrupted_markers_abort_entire_write(analysis, transcript, dirs):
    """一个文件的标记坏了就整次中止，不留下半套笔记。"""
    _write(analysis, transcript, dirs)
    viewpoint_path = dirs[1] / "Evaluation is the hidden cost nobody budgets for.md"
    viewpoint_path.write_text("标记被删光了的文件", encoding="utf-8")

    main_path = dirs[0] / "2026-08-01 How Teams Get the Bottleneck Wrong.md"
    before = main_path.read_text("utf-8")

    analysis["meta"]["thesis_en"] = "Yet another different thesis statement here."
    with pytest.raises(VaultWriteError, match="找不到 itmo 生成区标记"):
        _write(analysis, transcript, dirs)

    # 主笔记不应被改动
    assert main_path.read_text("utf-8") == before


def test_untouched_placeholder_does_not_count_as_user_content(analysis, transcript, dirs):
    """否则每次重跑都会对每篇笔记误报「已保留你写的内容」。"""
    _write(analysis, transcript, dirs)
    result = _write(analysis, transcript, dirs)
    assert not result.preserved


def test_dry_run_writes_nothing(analysis, transcript, dirs):
    """连目录都不能建——dry-run 跑在真 vault 上时不该留下任何痕迹。"""
    interview_dir, viewpoint_dir = dirs
    result = _write(analysis, transcript, dirs, dry_run=True)

    assert len(result.created) == 2
    assert not any(path.exists() for path in result.created)
    assert not interview_dir.exists()
    assert not viewpoint_dir.exists()


def test_orphan_viewpoint_notes_are_reported_not_deleted(analysis, transcript, dirs):
    _write(analysis, transcript, dirs)
    orphan = dirs[1] / "An old viewpoint from a previous run.md"
    # 用 itmo 真正会写出的带引号形式，避免测试和实现各说各话
    orphan.write_text(
        '---\nsource: "[[2026-08-01 How Teams Get the Bottleneck Wrong]]"\n---\n旧内容',
        encoding="utf-8",
    )

    result = _write(analysis, transcript, dirs)
    assert orphan in result.orphans
    assert orphan.exists()


def test_low_confidence_viewpoint_is_flagged_in_both_notes(analysis, transcript, dirs):
    analysis["viewpoints"][0]["speaker_confidence"] = 0.5
    _write(analysis, transcript, dirs)

    main = (dirs[0] / "2026-08-01 How Teams Get the Bottleneck Wrong.md").read_text("utf-8")
    viewpoint = (
        dirs[1] / "Evaluation is the hidden cost nobody budgets for.md"
    ).read_text("utf-8")
    assert "归属待确认" in main
    assert "归属待确认" in viewpoint


def _wikilinks(text: str) -> set[str]:
    import re

    return {m.group(1).split("|")[0] for m in re.finditer(r"\[\[([^\]]+)\]\]", text)}


def test_every_wikilink_resolves_to_an_existing_note(analysis, transcript, dirs):
    """双链靠文件名解析。链接文字和文件名不一致，整个知识网就是断的。"""
    interview_dir, viewpoint_dir = dirs
    _write(analysis, transcript, dirs)

    existing = {p.stem for p in interview_dir.rglob("*.md")}
    for note in interview_dir.rglob("*.md"):
        for link in _wikilinks(note.read_text("utf-8")):
            assert link in existing, f"{note.name} 里的 [[{link}]] 指向不存在的笔记"

    assert viewpoint_dir.exists()


def test_wikilinks_resolve_when_title_contains_unsafe_characters(analysis, transcript, dirs):
    """标题里的 [] # ^ 会被从文件名剔除，链接文字必须同样处理。"""
    analysis["viewpoints"][0]["title_en"] = "Why #1 [priorities] are the ^real constraint"
    interview_dir, _ = dirs
    _write(analysis, transcript, dirs)

    existing = {p.stem for p in interview_dir.rglob("*.md")}
    main = interview_dir / "2026-08-01 How Teams Get the Bottleneck Wrong.md"
    links = _wikilinks(main.read_text("utf-8"))
    assert links
    for link in links:
        assert link in existing, f"[[{link}]] 指向不存在的笔记"


def test_title_with_path_traversal_cannot_escape_directory(analysis, transcript, dirs):
    analysis["viewpoints"][0]["title_en"] = "../../escaped note title here"
    _write(analysis, transcript, dirs)
    assert not (dirs[1].parent.parent.parent / "escaped-note-title-here.md").exists()


def test_user_region_placeholder_is_written_once(analysis, transcript, dirs):
    _write(analysis, transcript, dirs)
    main_path = dirs[0] / "2026-08-01 How Teams Get the Bottleneck Wrong.md"
    text = main_path.read_text("utf-8")
    assert text.count(MINE_START) == 1
    assert text.count(MINE_END) == 1

    _write(analysis, transcript, dirs)
    text = main_path.read_text("utf-8")
    assert text.count(MINE_START) == 1


def test_timestamped_url_builds_youtube_deeplink():
    assert (
        timestamped_url("https://www.youtube.com/watch?v=abc", 125_000)
        == "https://www.youtube.com/watch?v=abc&t=125s"
    )
    assert timestamped_url("https://youtu.be/abc", 60_000) == "https://youtu.be/abc?t=60s"
    assert timestamped_url("https://example.com/ep", 60_000) == "https://example.com/ep"
    assert timestamped_url("https://youtu.be/abc", None) == "https://youtu.be/abc"


def test_table_cells_escape_pipes(analysis, transcript, dirs):
    analysis["expressions"][0]["meaning_zh"] = "含有 | 竖线 | 的释义"
    _write(analysis, transcript, dirs)
    text = (dirs[0] / "2026-08-01 How Teams Get the Bottleneck Wrong.md").read_text("utf-8")
    assert "含有 \\| 竖线 \\| 的释义" in text
