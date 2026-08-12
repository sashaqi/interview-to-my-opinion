"""统一的文字稿数据模型。

所有来源（YouTube json3、vtt、srt、纯文本）都归一化到 Transcript，
下游的分析与渲染只认这一个形状。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

# 归一化后用于引文校验的空白折叠
_WHITESPACE = re.compile(r"\s+")


def normalize_for_match(text: str) -> str:
    """折叠空白并小写，用于「引文是否真的出现在原文里」的比对。"""
    return _WHITESPACE.sub(" ", text).strip().lower()


def format_timestamp(ms: int) -> str:
    """毫秒 → H:MM:SS 或 M:SS。"""
    total_seconds = max(0, ms) // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


@dataclass(frozen=True)
class Segment:
    """一条字幕。start_ms 为 None 表示来源没有时间信息（如纯文本文字稿）。"""

    text: str
    start_ms: int | None = None
    duration_ms: int | None = None

    @property
    def timestamp(self) -> str | None:
        return None if self.start_ms is None else format_timestamp(self.start_ms)


@dataclass(frozen=True)
class Paragraph:
    """合并后的段落，是喂给分析层的基本单位。"""

    text: str
    start_ms: int | None = None
    index: int = 0

    @property
    def timestamp(self) -> str | None:
        return None if self.start_ms is None else format_timestamp(self.start_ms)


@dataclass
class SourceMeta:
    """来源元信息。字段全部可选，因为不同来源能拿到的信息差异很大。"""

    source_url: str = ""
    source_type: str = ""
    source_id: str = ""
    title: str = ""
    channel: str = ""
    description: str = ""
    published: str = ""
    duration_seconds: int | None = None
    language: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Transcript:
    """归一化后的完整文字稿。"""

    meta: SourceMeta
    segments: list[Segment] = field(default_factory=list)
    paragraphs: list[Paragraph] = field(default_factory=list)
    has_timestamps: bool = False

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.paragraphs)

    def word_count(self) -> int:
        return len(self.full_text.split())

    def contains(self, quote: str) -> bool:
        """引文是否出现在原文中（空白折叠后的子串匹配）。"""
        needle = normalize_for_match(quote)
        if not needle:
            return False
        return needle in normalize_for_match(self.full_text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "has_timestamps": self.has_timestamps,
            "word_count": self.word_count(),
            "paragraphs": [
                {"index": p.index, "start_ms": p.start_ms, "timestamp": p.timestamp, "text": p.text}
                for p in self.paragraphs
            ],
            "segments": [
                {"start_ms": s.start_ms, "duration_ms": s.duration_ms, "text": s.text}
                for s in self.segments
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Transcript:
        meta = SourceMeta(**payload.get("meta", {}))
        segments = [
            Segment(
                text=item["text"],
                start_ms=item.get("start_ms"),
                duration_ms=item.get("duration_ms"),
            )
            for item in payload.get("segments", [])
        ]
        paragraphs = [
            Paragraph(text=item["text"], start_ms=item.get("start_ms"), index=item.get("index", i))
            for i, item in enumerate(payload.get("paragraphs", []))
        ]
        return cls(
            meta=meta,
            segments=segments,
            paragraphs=paragraphs,
            has_timestamps=payload.get("has_timestamps", False),
        )
