"""字幕格式解析。

支持 YouTube json3、WebVTT、SubRip、纯文本。自动生成的字幕带滚动重复
（同一句话随着新词加入被反复重发），解析时必须去重，否则文字稿会膨胀
数倍并让分析层重复提取同一个观点。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Segment


class TranscriptParseError(RuntimeError):
    """字幕内容无法解析。"""


# [Music] / [Applause] / (laughs) 这类非语音标注对观点提炼没有价值
_SOUND_TAG = re.compile(r"^[\[\(][^\]\)]*[\]\)]$")
_INLINE_TAG = re.compile(r"[\[\(](?:music|applause|laughter|laughs|inaudible)[^\]\)]*[\]\)]", re.I)
_VTT_TAG = re.compile(r"</?(?:c|v|i|b|u)[^>]*>")
_VTT_TIMING = re.compile(
    r"(?P<start>\d{2,}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(?P<end>\d{2,}:\d{2}:\d{2}[.,]\d{3})"
)
_SRT_TIMING = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


def _clean(text: str) -> str:
    text = _VTT_TAG.sub("", text)
    text = _INLINE_TAG.sub(" ", text)
    text = text.replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def _is_noise(text: str) -> bool:
    return not text or _SOUND_TAG.match(text) is not None


def _timecode_to_ms(value: str) -> int:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours, minutes, seconds = "0", parts[0], parts[1]
    else:
        raise TranscriptParseError(f"无法解析时间码：{value!r}")
    return int(
        (int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000
    )


def _dedupe_rolling(segments: list[Segment]) -> list[Segment]:
    """去掉自动字幕的滚动重复。

    自动字幕会把同一句话逐词重发，前一条通常是后一条的前缀。规则：
    当上一条是当前条的前缀时丢弃上一条，保留信息更完整的那条。
    """
    result: list[Segment] = []
    for segment in segments:
        text = segment.text
        while result:
            previous = result[-1].text
            if previous == text or text.startswith(previous + " ") or text == previous:
                result.pop()
                continue
            break
        if result and result[-1].text == text:
            continue
        result.append(segment)
    return result


def parse_json3(content: str) -> list[Segment]:
    """解析 YouTube json3 字幕。"""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise TranscriptParseError(f"json3 内容不是合法 JSON：{exc}") from exc

    events = payload.get("events")
    if not isinstance(events, list):
        raise TranscriptParseError("json3 内容缺少 events 数组。")

    segments: list[Segment] = []
    for event in events:
        # aAppend 事件是滚动字幕的续写帧，内容与前一条重复
        if event.get("aAppend"):
            continue
        segs = event.get("segs")
        if not segs:
            continue
        text = _clean("".join(seg.get("utf8", "") for seg in segs))
        if _is_noise(text):
            continue
        segments.append(
            Segment(
                text=text,
                start_ms=event.get("tStartMs"),
                duration_ms=event.get("dDurationMs"),
            )
        )
    return _dedupe_rolling(segments)


def _parse_cue_based(content: str, timing: re.Pattern[str]) -> list[Segment]:
    segments: list[Segment] = []
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").strip())
    for block in blocks:
        lines = block.strip().split("\n")
        match = None
        text_start = 0
        for index, line in enumerate(lines):
            match = timing.search(line)
            if match:
                text_start = index + 1
                break
        if not match:
            continue
        text = _clean(" ".join(lines[text_start:]))
        if _is_noise(text):
            continue
        start_ms = _timecode_to_ms(match.group("start"))
        end_ms = _timecode_to_ms(match.group("end"))
        segments.append(
            Segment(text=text, start_ms=start_ms, duration_ms=max(0, end_ms - start_ms))
        )
    if not segments:
        raise TranscriptParseError("未找到任何带时间码的字幕块。")
    return _dedupe_rolling(segments)


def parse_vtt(content: str) -> list[Segment]:
    """解析 WebVTT。"""
    return _parse_cue_based(content, _VTT_TIMING)


def parse_srt(content: str) -> list[Segment]:
    """解析 SubRip。"""
    return _parse_cue_based(content, _SRT_TIMING)


def parse_plain_text(content: str) -> list[Segment]:
    """解析无时间信息的纯文本/Markdown 文字稿，按空行切段。"""
    normalized = content.replace("\r\n", "\n")
    blocks = [b.strip() for b in re.split(r"\n\s*\n", normalized) if b.strip()]
    if len(blocks) <= 1:
        # 整份文稿没有空行分段时按行切；paragraphs.py 会再按字数合并回去
        blocks = [line.strip() for line in normalized.split("\n") if line.strip()]
    segments = [Segment(text=_clean(block)) for block in blocks]
    segments = [s for s in segments if not _is_noise(s.text)]
    if not segments:
        raise TranscriptParseError("文字稿为空。")
    return segments


_PARSERS = {
    ".json3": parse_json3,
    ".json": parse_json3,
    ".vtt": parse_vtt,
    ".srt": parse_srt,
    ".txt": parse_plain_text,
    ".md": parse_plain_text,
}


def parse_file(path: Path) -> list[Segment]:
    """按扩展名选择解析器。"""
    suffix = path.suffix.lower()
    parser = _PARSERS.get(suffix)
    if parser is None:
        supported = ", ".join(sorted(_PARSERS))
        raise TranscriptParseError(f"不支持的文字稿格式 {suffix!r}。支持：{supported}")
    content = path.read_text(encoding="utf-8", errors="replace")
    if not content.strip():
        raise TranscriptParseError(f"文件为空：{path}")
    return parser(content)
