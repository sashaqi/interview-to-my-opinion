"""YouTube 采集：元信息 + 单条英文字幕轨。

刻意不走 yt-dlp 的批量字幕下载。实测 `--sub-langs "en.*"` 会连带拉取
几十条机翻轨并触发 HTTP 429，且字幕失败会连带吞掉 info.json。这里改为
先取一次元信息，再从中挑出唯一一条目标轨手动下载。
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ..transcript.models import Segment, SourceMeta
from ..transcript.parsers import parse_json3, parse_srt, parse_vtt

MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2.0

# json3 带最完整的时间信息，优先；其余按可解析性排序
PREFERRED_FORMATS = ("json3", "vtt", "srv1", "srt")

_FORMAT_PARSERS = {
    "json3": parse_json3,
    "vtt": parse_vtt,
    "srt": parse_srt,
    "srv1": parse_vtt,
}


class YouTubeFetchError(RuntimeError):
    """YouTube 元信息或字幕获取失败。"""


@dataclass(frozen=True)
class SubtitleTrack:
    lang: str
    ext: str
    url: str
    is_automatic: bool


def _select_track(info: dict, sub_langs: tuple[str, ...]) -> SubtitleTrack:
    """按语言优先级挑一条轨，人工字幕优先于自动字幕。"""
    manual = info.get("subtitles") or {}
    automatic = info.get("automatic_captions") or {}

    for pool, is_automatic in ((manual, False), (automatic, True)):
        for lang in sub_langs:
            formats = pool.get(lang)
            if not formats:
                continue
            by_ext = {f.get("ext"): f for f in formats if f.get("url")}
            for ext in PREFERRED_FORMATS:
                if ext in by_ext:
                    return SubtitleTrack(
                        lang=lang, ext=ext, url=by_ext[ext]["url"], is_automatic=is_automatic
                    )

    available = sorted(set(manual) | set(automatic))
    preview = ", ".join(available[:15]) if available else "无"
    raise YouTubeFetchError(
        f"该视频没有可用的英文字幕（想要：{', '.join(sub_langs)}；实际可用：{preview}）。\n"
        "v1 只从字幕取文字稿。如果你手上有文字稿，用 --transcript-file 直接喂进来。"
    )


def _download_with_retry(ydl, url: str) -> str:
    """下载字幕内容，对 429 和网络抖动做指数退避。"""
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return ydl.urlopen(url).read().decode("utf-8", errors="replace")
        except Exception as exc:  # yt-dlp 抛多种自定义异常
            last_error = exc
            message = str(exc)
            is_retryable = "429" in message or "timed out" in message.lower()
            if not is_retryable or attempt == MAX_RETRIES - 1:
                break
            time.sleep(BACKOFF_BASE_SECONDS * (2**attempt))

    raise YouTubeFetchError(
        f"字幕下载失败（重试 {MAX_RETRIES} 次）：{last_error}\n"
        "若是 429，等几分钟再试；或用 --transcript-file 绕开。"
    ) from last_error


def _build_meta(info: dict, track: SubtitleTrack) -> SourceMeta:
    upload_date = info.get("upload_date") or ""
    published = (
        f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        if len(upload_date) == 8
        else ""
    )
    return SourceMeta(
        source_url=info.get("webpage_url") or "",
        source_type="youtube",
        source_id=info.get("id") or "",
        title=info.get("title") or "",
        channel=info.get("channel") or info.get("uploader") or "",
        description=info.get("description") or "",
        published=published,
        duration_seconds=info.get("duration"),
        language=track.lang,
    )


def fetch_youtube(url: str, sub_langs: tuple[str, ...]) -> tuple[SourceMeta, list[Segment], bool]:
    """返回 (元信息, 字幕分段, 是否为自动生成字幕)。"""
    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise YouTubeFetchError("缺少 yt-dlp 依赖，运行 `uv sync` 安装。") from exc

    options = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with YoutubeDL(options) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as exc:
            raise YouTubeFetchError(f"无法读取视频信息：{exc}") from exc

        if info.get("_type") == "playlist":
            raise YouTubeFetchError("这是一个播放列表链接，请提供单个视频的链接。")

        track = _select_track(info, sub_langs)
        content = _download_with_retry(ydl, track.url)

    parser = _FORMAT_PARSERS.get(track.ext)
    if parser is None:
        raise YouTubeFetchError(f"字幕格式 {track.ext!r} 没有对应解析器。")

    segments = parser(content)
    if not segments:
        raise YouTubeFetchError("字幕下载成功但解析后为空，可能整轨都是音乐或掌声标注。")

    return _build_meta(info, track), segments, track.is_automatic
