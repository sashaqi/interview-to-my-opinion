"""采集编排：输入 → 归一化 Transcript。"""

from __future__ import annotations

from ..config import Config
from ..transcript.models import Transcript
from ..transcript.paragraphs import build_paragraphs
from .local import fetch_local
from .podcast import fetch_podcast
from .router import SourceType, detect_source
from .youtube import fetch_youtube


class FetchError(RuntimeError):
    """采集失败。"""


def build_transcript(
    source: str, config: Config, *, episode_title: str | None = None
) -> Transcript:
    """按来源类型采集并归一化成 Transcript。"""
    detection = detect_source(source)

    if detection.type is SourceType.YOUTUBE:
        meta, segments, _is_automatic = fetch_youtube(detection.source, config.sub_langs)
    elif detection.type is SourceType.LOCAL_TRANSCRIPT:
        meta, segments = fetch_local(detection.source)
    elif detection.type is SourceType.PODCAST_RSS:
        meta, segments = fetch_podcast(detection.source, episode_title=episode_title)
    elif detection.type is SourceType.APPLE_PODCAST:
        raise FetchError(
            "Apple Podcasts 页面本身不提供文字稿，需要节目的 RSS 地址。\n"
            "在节目页面找到 RSS 链接后直接传给 itmo，或用 --transcript-file 提供文字稿。"
        )
    else:
        raise FetchError(f"来源类型 {detection.type.value} 的采集尚未实现。")

    paragraphs = build_paragraphs(segments)
    if not paragraphs:
        raise FetchError("解析后没有得到任何段落，文字稿可能为空。")

    has_timestamps = any(p.start_ms is not None for p in paragraphs)
    return Transcript(
        meta=meta,
        segments=segments,
        paragraphs=paragraphs,
        has_timestamps=has_timestamps,
    )
