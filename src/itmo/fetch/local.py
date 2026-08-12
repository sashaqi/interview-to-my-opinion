"""本地文字稿采集。

这是「只用字幕」路线的逃生口：任何来源的文字稿都能从这里进入下游流程，
不引入音频下载和转写依赖。
"""

from __future__ import annotations

from pathlib import Path

from ..transcript.models import Segment, SourceMeta
from ..transcript.parsers import parse_file


class LocalTranscriptError(RuntimeError):
    """本地文字稿不可用。"""


def fetch_local(path_str: str) -> tuple[SourceMeta, list[Segment]]:
    """读取并解析本地文字稿。"""
    path = Path(path_str).expanduser()
    if not path.exists():
        raise LocalTranscriptError(f"文件不存在：{path}")
    if not path.is_file():
        raise LocalTranscriptError(f"不是文件：{path}")

    segments = parse_file(path)
    meta = SourceMeta(
        source_url="",
        source_type="local_transcript",
        source_id=path.stem,
        title=path.stem.replace("-", " ").replace("_", " ").strip(),
        language="en",
    )
    return meta, segments
