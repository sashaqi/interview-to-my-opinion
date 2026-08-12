"""输入分类。

只做分类，不下载、不联网、不检查文件是否存在。下游模块消费归一化后的类型。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse


class SourceType(str, Enum):
    YOUTUBE = "youtube"
    PODCAST_RSS = "podcast_rss"
    APPLE_PODCAST = "apple_podcast"
    LOCAL_TRANSCRIPT = "local_transcript"


class SourceRouterError(RuntimeError):
    """输入无法分类。"""


@dataclass(frozen=True)
class SourceDetection:
    type: SourceType
    source: str


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "music.youtube.com",
}

APPLE_PODCAST_HOSTS = {"podcasts.apple.com", "itunes.apple.com"}

RSS_EXTENSIONS = {".rss", ".xml", ".atom"}

TRANSCRIPT_EXTENSIONS = {".txt", ".md", ".vtt", ".srt", ".json3", ".json"}


def is_url(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _host(source: str) -> str:
    return urlparse(source).netloc.lower()


def is_youtube_url(source: str) -> bool:
    host = _host(source)
    return host in YOUTUBE_HOSTS or host.endswith(".youtube.com")


def is_apple_podcast_url(source: str) -> bool:
    return _host(source) in APPLE_PODCAST_HOSTS


def is_podcast_rss_url(source: str) -> bool:
    parsed = urlparse(source)
    path = parsed.path.lower()
    return Path(path).suffix in RSS_EXTENSIONS or "feed" in path or "rss" in path


def is_transcript_path(source: str) -> bool:
    return Path(source).expanduser().suffix.lower() in TRANSCRIPT_EXTENSIONS


def detect_source(source: str) -> SourceDetection:
    """分类用户输入。"""
    cleaned = source.strip()
    if not cleaned:
        raise SourceRouterError("输入为空。")

    if is_url(cleaned):
        if is_youtube_url(cleaned):
            return SourceDetection(SourceType.YOUTUBE, cleaned)
        if is_apple_podcast_url(cleaned):
            return SourceDetection(SourceType.APPLE_PODCAST, cleaned)
        if is_podcast_rss_url(cleaned):
            return SourceDetection(SourceType.PODCAST_RSS, cleaned)
        raise SourceRouterError(
            "无法识别的 URL。v1 支持 YouTube 视频链接、播客 RSS 地址和 Apple Podcasts 链接。\n"
            "如果你手上已有文字稿，可以用 --transcript-file 直接喂进来。"
        )

    if is_transcript_path(cleaned):
        return SourceDetection(SourceType.LOCAL_TRANSCRIPT, cleaned)

    raise SourceRouterError(
        f"无法识别的输入：{cleaned!r}\n"
        "支持的本地文字稿格式：" + ", ".join(sorted(TRANSCRIPT_EXTENSIONS))
    )
