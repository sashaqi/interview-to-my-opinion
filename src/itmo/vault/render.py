"""把 analysis.json 渲染成 Obsidian markdown。

渲染只负责生成区的内容。用户区由 markers 模块在首次创建时写入，之后不再触碰。
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from ..slugs import note_title
from ..transcript.models import Transcript, format_timestamp
from .markers import compose_note, wrap_generated, wrap_mine

ITMO_VERSION = 1

MAIN_MINE_HEADING = "## 我的观点"
MAIN_MINE_PLACEHOLDER = (
    "> 他说的哪一条我真的同意？哪一条我在工作里见过反例？\n"
    "> 如果我要把这个观点讲给同事听，我会加上什么他没说的东西？"
)

VIEWPOINT_MINE_HEADING = "## 我的印证"
VIEWPOINT_MINE_PLACEHOLDER = (
    "> 我见过的例子：\n"
    "> 我不同意的地方："
)

EXPRESSION_TYPE_LABELS = {
    "idiom": "习语",
    "collocation": "搭配",
    "sentence_frame": "句型",
    "term": "术语",
}


def timestamped_url(source_url: str, start_ms: int | None) -> str:
    """生成回跳原视频的深链。非 YouTube 或无时间戳时返回原 URL。"""
    if not source_url or start_ms is None:
        return source_url

    host = urlparse(source_url).netloc.lower()
    if "youtube.com" not in host and "youtu.be" not in host:
        return source_url

    separator = "&" if "?" in source_url else "?"
    return f"{source_url}{separator}t={start_ms // 1000}s"


def _escape_table_cell(text: str) -> str:
    """表格单元格里的竖线和换行会破坏 markdown 表格。"""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _paragraph_start_ms(transcript: Transcript, index: int | None) -> int | None:
    if index is None or index >= len(transcript.paragraphs):
        return None
    return transcript.paragraphs[index].start_ms


def _duration_text(seconds: int | None) -> str:
    return format_timestamp(seconds * 1000) if seconds else ""


def _needs_review(viewpoint: dict[str, Any], threshold: float) -> bool:
    return viewpoint.get("speaker_confidence", 1.0) < threshold


# --------------------------------------------------------------------------
# 主笔记
# --------------------------------------------------------------------------


def main_frontmatter(analysis: dict[str, Any], transcript: Transcript) -> dict[str, object]:
    meta = analysis["meta"]
    source = transcript.meta
    return {
        "title": source.title or meta.get("thesis_en", "")[:60],
        "type": "interview",
        "interviewee": meta.get("interviewee", ""),
        "interviewer": meta.get("interviewer", ""),
        "channel": source.channel,
        "source_url": source.source_url,
        "published": source.published,
        "duration": _duration_text(source.duration_seconds),
        "tags": ["interview", *meta.get("domain_tags", [])],
        "status": "inbox",
        "itmo_version": ITMO_VERSION,
    }


def _render_viewpoint_index(
    analysis: dict[str, Any], transcript: Transcript, threshold: float
) -> str:
    lines = ["## 观点索引", ""]
    for viewpoint in analysis["viewpoints"]:
        start_ms = _paragraph_start_ms(transcript, viewpoint.get("paragraph_index"))
        # 必须与 writer 写出的文件名用同一个函数，否则 wikilink 解析不到
        link_target = note_title(viewpoint["title_en"])
        parts = [f"- [[{link_target}]] — {viewpoint['title_zh']}"]

        if start_ms is not None and transcript.meta.source_url:
            link = timestamped_url(transcript.meta.source_url, start_ms)
            parts.append(f"[⏱ {format_timestamp(start_ms)}]({link})")
        if _needs_review(viewpoint, threshold):
            parts.append(
                f"⚠️ 归属待确认（{viewpoint.get('speaker_confidence', 0):.0%}）"
            )

        lines.append(" · ".join(parts))
    return "\n".join(lines)


def _render_expressions(analysis: dict[str, Any]) -> str:
    expressions = analysis.get("expressions", [])
    if not expressions:
        return ""

    lines = [
        "## 关键表达 & 句型骨架",
        "",
        "| 表达 | 类型 | 中文释义 | 原句 | 我的例句 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for expression in expressions:
        label = EXPRESSION_TYPE_LABELS.get(expression["type"], expression["type"])
        lines.append(
            "| "
            + " | ".join(
                _escape_table_cell(cell)
                for cell in (
                    f"**{expression['text']}**",
                    label,
                    expression["meaning_zh"],
                    expression["source_sentence"],
                    expression["your_example"],
                )
            )
            + " |"
        )
    return "\n".join(lines)


def _render_socratic(analysis: dict[str, Any]) -> str:
    questions = analysis.get("socratic_questions", [])
    if not questions:
        return ""

    lines = ["## 苏格拉底追问卡", ""]
    for question in questions:
        lines.extend(
            [
                f"> [!question] {question['question_en']}",
                f"> **难在**：{question['why_hard_zh']}",
                f"> **角度**：{question['angle_en']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def render_main_body(
    analysis: dict[str, Any], transcript: Transcript, threshold: float
) -> str:
    meta = analysis["meta"]
    source = transcript.meta

    header_bits = [f"**{meta.get('interviewee', '')}**"]
    if source.channel:
        header_bits.append(
            f"[{source.channel}]({source.source_url})" if source.source_url else source.channel
        )
    if source.published:
        header_bits.append(source.published)

    sections = [
        f"# {source.title or meta.get('interviewee', '访谈笔记')}",
        "",
        " · ".join(header_bits),
        "",
        "> [!abstract] 核心主张",
        f"> {meta.get('thesis_en', '')}",
        ">",
        f"> {meta.get('thesis_zh', '')}",
        "",
        _render_viewpoint_index(analysis, transcript, threshold),
    ]

    for block in (_render_expressions(analysis), _render_socratic(analysis)):
        if block:
            sections.extend(["", block])

    return "\n".join(sections)


def render_main_note(
    analysis: dict[str, Any], transcript: Transcript, threshold: float
) -> str:
    """渲染完整主笔记（首次创建用）。"""
    from .markers import render_frontmatter

    body = "\n\n".join(
        [
            wrap_generated(render_main_body(analysis, transcript, threshold)),
            wrap_mine(MAIN_MINE_HEADING, MAIN_MINE_PLACEHOLDER),
        ]
    )
    return compose_note(render_frontmatter(main_frontmatter(analysis, transcript)), body)


# --------------------------------------------------------------------------
# 观点原子笔记
# --------------------------------------------------------------------------


def viewpoint_frontmatter(
    viewpoint: dict[str, Any],
    analysis: dict[str, Any],
    transcript: Transcript,
    main_note_name: str,
) -> dict[str, object]:
    start_ms = _paragraph_start_ms(transcript, viewpoint.get("paragraph_index"))
    tags = ["viewpoint", *analysis["meta"].get("domain_tags", []), *viewpoint.get("tags", [])]
    return {
        "type": "viewpoint",
        "viewpoint_id": viewpoint["id"],
        "source": f"[[{main_note_name}]]",
        "source_url": transcript.meta.source_url,
        "speaker": viewpoint.get("speaker", ""),
        "attribution": viewpoint.get("attribution", ""),
        "speaker_confidence": viewpoint.get("speaker_confidence", 0),
        "timestamp": format_timestamp(start_ms) if start_ms is not None else "",
        "tags": list(dict.fromkeys(tags)),
        "status": "inbox",
        "itmo_version": ITMO_VERSION,
    }


def render_viewpoint_body(
    viewpoint: dict[str, Any], transcript: Transcript, main_note_name: str, threshold: float
) -> str:
    start_ms = _paragraph_start_ms(transcript, viewpoint.get("paragraph_index"))

    sections = [f"# {viewpoint['title_en']}", "", f"> {viewpoint['title_zh']}", ""]

    if _needs_review(viewpoint, threshold):
        sections.extend(
            [
                "> [!warning] 归属待确认",
                f"> 字幕不含说话人标签，这条观点是推断归属于 **{viewpoint.get('speaker', '?')}** 的，"
                f"把握约 {viewpoint.get('speaker_confidence', 0):.0%}。",
                "> 引用前请回听原片确认。",
                "",
            ]
        )

    sections.extend(
        [
            "## Claim",
            "",
            viewpoint["claim_en"],
            "",
            "## 他的论证",
            "",
            viewpoint["reasoning_en"],
            "",
            "## 原文引证",
            "",
            f"> {viewpoint['evidence_quote']}",
        ]
    )

    if start_ms is not None and transcript.meta.source_url:
        link = timestamped_url(transcript.meta.source_url, start_ms)
        sections.append(f"> — [⏱ {format_timestamp(start_ms)}]({link})")

    sections.extend(
        [
            "",
            "## 30 秒复述",
            "",
            viewpoint["retelling_30s"],
            "",
            "## 2 分钟复述",
            "",
            viewpoint["retelling_2min"],
            "",
            "## 反方视角",
            "",
            viewpoint["counterpoint_en"],
            "",
            f"来源：[[{main_note_name}]]",
        ]
    )
    return "\n".join(sections)


def render_viewpoint_note(
    viewpoint: dict[str, Any],
    analysis: dict[str, Any],
    transcript: Transcript,
    main_note_name: str,
    threshold: float,
) -> str:
    """渲染完整观点笔记（首次创建用）。"""
    from .markers import render_frontmatter

    body = "\n\n".join(
        [
            wrap_generated(
                render_viewpoint_body(viewpoint, transcript, main_note_name, threshold)
            ),
            wrap_mine(VIEWPOINT_MINE_HEADING, VIEWPOINT_MINE_PLACEHOLDER),
        ]
    )
    frontmatter = viewpoint_frontmatter(viewpoint, analysis, transcript, main_note_name)
    return compose_note(render_frontmatter(frontmatter), body)
