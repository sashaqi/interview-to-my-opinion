"""写入 vault。

首次创建写完整笔记（含用户区），已存在则只替换生成区。任何一个文件的
标记损坏都会中止整次写入——宁可什么都不写，也不要写一半。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..slugs import interview_note_name, note_title
from ..transcript.models import Transcript
from .markers import MarkerError, has_user_content, merge_note
from .render import (
    MAIN_MINE_PLACEHOLDER,
    VIEWPOINT_MINE_PLACEHOLDER,
    main_frontmatter,
    render_main_body,
    render_main_note,
    render_viewpoint_body,
    render_viewpoint_note,
    viewpoint_frontmatter,
)

# 首次创建写入的提示文字，判断「用户是否真的写了东西」时要排除
PLACEHOLDERS = (MAIN_MINE_PLACEHOLDER, VIEWPOINT_MINE_PLACEHOLDER)


class VaultWriteError(RuntimeError):
    """写入 vault 失败。"""


@dataclass
class PlannedWrite:
    path: Path
    content: str
    is_new: bool
    preserved_user_content: bool = False


@dataclass
class WriteResult:
    created: list[Path] = field(default_factory=list)
    updated: list[Path] = field(default_factory=list)
    preserved: list[Path] = field(default_factory=list)
    orphans: list[Path] = field(default_factory=list)


def _resolve_within(base: Path, name: str) -> Path:
    """拼路径并确认没有逃出 base，防止标题里的 ../ 写到 vault 外面。"""
    candidate = (base / f"{name}.md").resolve()
    base_resolved = base.resolve()
    if base_resolved != candidate.parent and base_resolved not in candidate.parents:
        raise VaultWriteError(f"笔记路径逃出了目标目录：{candidate}")
    return candidate


def _plan_write(path: Path, fresh: str, values: dict[str, Any], generated_body: str) -> PlannedWrite:
    if not path.exists():
        return PlannedWrite(path=path, content=fresh, is_new=True)

    existing = path.read_text(encoding="utf-8")
    try:
        merged = merge_note(existing, values, generated_body)
    except MarkerError as exc:
        raise VaultWriteError(f"{path}\n{exc}") from exc

    return PlannedWrite(
        path=path,
        content=merged,
        is_new=False,
        preserved_user_content=has_user_content(existing, PLACEHOLDERS),
    )


def _find_orphans(directory: Path, main_note_name: str, current_files: set[Path]) -> list[Path]:
    """找出属于这期访谈、但本次分析里已经不存在的旧观点笔记。

    只报告不删除。用户可能已经在里面写了东西，删除的决定权不在程序。
    """
    if not directory.exists():
        return []

    # frontmatter 里 wikilink 会被加引号（source: "[[x]]"），所以只认链接本身
    marker = f"[[{main_note_name}]]"
    orphans = []
    for path in directory.glob("*.md"):
        if path.resolve() in current_files:
            continue
        try:
            head = path.read_text(encoding="utf-8")[:1000]
        except OSError:
            continue
        if marker in head:
            orphans.append(path)
    return orphans


def write_notes(
    analysis: dict[str, Any],
    transcript: Transcript,
    *,
    interview_dir: Path,
    viewpoint_dir: Path,
    threshold: float,
    dry_run: bool = False,
) -> WriteResult:
    """渲染并写入主笔记与观点原子笔记。"""
    main_note_name = interview_note_name(
        transcript.meta.published, transcript.meta.title or analysis["meta"].get("interviewee", "")
    )

    # dry-run 必须完全不碰文件系统，否则「只看看」也会在 vault 里留下空目录
    if not dry_run:
        interview_dir.mkdir(parents=True, exist_ok=True)
        viewpoint_dir.mkdir(parents=True, exist_ok=True)

    planned: list[PlannedWrite] = [
        _plan_write(
            _resolve_within(interview_dir, main_note_name),
            render_main_note(analysis, transcript, threshold),
            main_frontmatter(analysis, transcript),
            render_main_body(analysis, transcript, threshold),
        )
    ]

    for viewpoint in analysis["viewpoints"]:
        planned.append(
            _plan_write(
                # 文件名必须与主笔记里的 [[title_en]] 逐字一致，否则双链解析不了
                _resolve_within(viewpoint_dir, note_title(viewpoint["title_en"])),
                render_viewpoint_note(
                    viewpoint, analysis, transcript, main_note_name, threshold
                ),
                viewpoint_frontmatter(viewpoint, analysis, transcript, main_note_name),
                render_viewpoint_body(viewpoint, transcript, main_note_name, threshold),
            )
        )

    result = WriteResult(
        orphans=_find_orphans(
            viewpoint_dir, main_note_name, {p.path.resolve() for p in planned}
        )
    )

    # 全部规划成功后才落盘，避免标记损坏时写出半套笔记
    for item in planned:
        if not dry_run:
            item.path.write_text(item.content, encoding="utf-8")
        (result.created if item.is_new else result.updated).append(item.path)
        if item.preserved_user_content:
            result.preserved.append(item.path)

    return result
