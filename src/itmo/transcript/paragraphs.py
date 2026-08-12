"""把零散字幕合并成段落。

字幕以 2-5 秒为单位切分，直接喂给分析层会丢失论述结构。这里按停顿时长
和字数把它们聚成段落，并保留段落起始时间戳，用于生成回跳原视频的深链。
"""

from __future__ import annotations

from .models import Paragraph, Segment

# 超过这个停顿视为话题切换
PAUSE_BREAK_MS = 2000
# 段落目标字数，达到后在下一个句末标点处断开
MAX_PARAGRAPH_WORDS = 160
# 硬上限。自动字幕可能整段没有标点，没有这道闸就会产出一个巨型段落
HARD_MAX_WORDS_RATIO = 2
# 句末标点处才允许因字数超限而断段，避免把句子劈开
SENTENCE_END = (".", "?", "!", '."', '?"', '!"', ".)", "?)", "!)")


def _ends_sentence(text: str) -> bool:
    return text.rstrip().endswith(SENTENCE_END)


def build_paragraphs(
    segments: list[Segment],
    *,
    pause_break_ms: int = PAUSE_BREAK_MS,
    max_words: int = MAX_PARAGRAPH_WORDS,
) -> list[Paragraph]:
    """合并字幕为段落。

    断段条件（满足其一）：
    - 与上一条字幕之间的停顿超过 pause_break_ms
    - 当前段字数已超过 max_words 且上一条以句末标点结尾
    - 当前段字数达到硬上限（防止无标点字幕产出巨型段落）
    """
    hard_max_words = max_words * HARD_MAX_WORDS_RATIO
    if not segments:
        return []

    paragraphs: list[Paragraph] = []
    buffer: list[str] = []
    buffer_words = 0
    start_ms: int | None = None
    previous_end: int | None = None

    def flush() -> None:
        nonlocal buffer, buffer_words, start_ms
        if buffer:
            paragraphs.append(
                Paragraph(text=" ".join(buffer), start_ms=start_ms, index=len(paragraphs))
            )
        buffer = []
        buffer_words = 0
        start_ms = None

    for segment in segments:
        gap_break = (
            previous_end is not None
            and segment.start_ms is not None
            and segment.start_ms - previous_end > pause_break_ms
        )
        length_break = buffer_words >= max_words and buffer and _ends_sentence(buffer[-1])
        hard_break = buffer_words >= hard_max_words

        if buffer and (gap_break or length_break or hard_break):
            flush()

        if not buffer:
            start_ms = segment.start_ms
        buffer.append(segment.text)
        buffer_words += len(segment.text.split())

        if segment.start_ms is not None:
            previous_end = segment.start_ms + (segment.duration_ms or 0)

    flush()
    return paragraphs
