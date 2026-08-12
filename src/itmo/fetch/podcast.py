"""播客采集。

只走文字稿路线，不下载音频、不转写。绝大多数播客不发布文字稿，所以这条
路径失败是常态——失败时必须给出明确的下一步（`--transcript-file`），
而不是含糊报错让用户猜。

RSS 2.0 的 `<podcast:transcript>` 标签（Podcasting 2.0 规范）是唯一可靠的
文字稿来源。Apple Podcasts 页面本身不提供文字稿，只能从中找回 RSS。
"""

from __future__ import annotations

import re
from typing import Any

from ..transcript.models import Segment, SourceMeta
from ..transcript.parsers import (
    TranscriptParseError,
    parse_json3,
    parse_plain_text,
    parse_srt,
    parse_vtt,
)

# 按可解析性排序；html 需要额外处理，暂不支持
TRANSCRIPT_TYPE_PARSERS = {
    "application/json": parse_json3,
    "application/x-subrip": parse_srt,
    "application/srt": parse_srt,
    "text/vtt": parse_vtt,
    "text/plain": parse_plain_text,
}

NO_TRANSCRIPT_HELP = (
    "这个播客的 RSS 里没有 <podcast:transcript> 文字稿标签。\n"
    "v1 只从文字稿提取观点，不下载音频也不做语音转写，所以这一期无法自动处理。\n"
    "可行的做法：从节目页面找到官方文字稿，或用任意转写工具生成一份，\n"
    "然后用 `itmo fetch --transcript-file <路径>` 走同样的后续流程。"
)


class PodcastFetchError(RuntimeError):
    """播客文字稿不可用。"""


def _pick_episode(feed: Any, episode_title: str | None) -> Any:
    entries = getattr(feed, "entries", [])
    if not entries:
        raise PodcastFetchError("这个 RSS 里没有任何单集。")

    if not episode_title:
        return entries[0]

    needle = episode_title.strip().lower()
    for entry in entries:
        if needle in (entry.get("title") or "").lower():
            return entry

    available = "\n".join(f"  - {e.get('title', '')}" for e in entries[:10])
    raise PodcastFetchError(f"没有找到标题含 {episode_title!r} 的单集。最近几期：\n{available}")


def _find_transcript_link(entry: Any) -> tuple[str, str]:
    """返回 (url, mime type)。找不到时抛错。"""
    # feedparser 把命名空间标签解析成 podcast_transcript / links
    candidates: list[dict[str, str]] = []

    transcript = entry.get("podcast_transcript")
    if isinstance(transcript, dict):
        candidates.append(transcript)
    elif isinstance(transcript, list):
        candidates.extend(item for item in transcript if isinstance(item, dict))

    for link in entry.get("links", []):
        if link.get("rel") == "transcript" or "transcript" in (link.get("type") or ""):
            candidates.append(link)

    for candidate in candidates:
        url = candidate.get("url") or candidate.get("href")
        mime = (candidate.get("type") or "").lower()
        if url and mime in TRANSCRIPT_TYPE_PARSERS:
            return url, mime

    # 有标签但格式不支持，和完全没有标签要分开说
    for candidate in candidates:
        url = candidate.get("url") or candidate.get("href")
        if url:
            mime = candidate.get("type") or "未标注类型"
            supported = ", ".join(sorted(TRANSCRIPT_TYPE_PARSERS))
            raise PodcastFetchError(
                f"这一期的文字稿格式是 {mime}，暂不支持。支持的格式：{supported}\n"
                f"你可以自己下载 {url} 转成 .txt 后用 --transcript-file 喂进来。"
            )

    raise PodcastFetchError(NO_TRANSCRIPT_HELP)


def _published_date(entry: Any) -> str:
    parsed = entry.get("published_parsed")
    if not parsed:
        return ""
    return f"{parsed.tm_year:04d}-{parsed.tm_mon:02d}-{parsed.tm_mday:02d}"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def fetch_podcast(
    feed_url: str, *, episode_title: str | None = None
) -> tuple[SourceMeta, list[Segment]]:
    """从播客 RSS 取指定单集的文字稿。"""
    try:
        import feedparser
    except ModuleNotFoundError as exc:
        raise PodcastFetchError("缺少 feedparser 依赖，运行 `uv sync` 安装。") from exc

    feed = feedparser.parse(feed_url)
    if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
        raise PodcastFetchError(f"无法解析这个 RSS：{getattr(feed, 'bozo_exception', '未知错误')}")

    entry = _pick_episode(feed, episode_title)
    url, mime = _find_transcript_link(entry)

    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise PodcastFetchError(f"文字稿下载失败（{url}）：{exc}") from exc

    try:
        segments = TRANSCRIPT_TYPE_PARSERS[mime](content)
    except TranscriptParseError as exc:
        raise PodcastFetchError(f"文字稿解析失败：{exc}") from exc

    meta = SourceMeta(
        source_url=entry.get("link") or feed_url,
        source_type="podcast",
        source_id=entry.get("id") or entry.get("link") or "",
        title=entry.get("title") or "",
        channel=getattr(feed.feed, "title", "") if hasattr(feed, "feed") else "",
        description=_strip_html(entry.get("summary", ""))[:2000],
        published=_published_date(entry),
        language="en",
    )
    return meta, segments
