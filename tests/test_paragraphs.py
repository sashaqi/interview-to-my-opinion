"""段落合并测试。"""

from __future__ import annotations

from itmo.transcript.models import Segment
from itmo.transcript.paragraphs import build_paragraphs


def _seg(text: str, start_ms: int, duration_ms: int = 1000) -> Segment:
    return Segment(text=text, start_ms=start_ms, duration_ms=duration_ms)


def test_merges_adjacent_segments_into_one_paragraph():
    segments = [_seg("We build the thing.", 0), _seg("Then we ship it.", 1000)]
    paragraphs = build_paragraphs(segments)
    assert len(paragraphs) == 1
    assert paragraphs[0].text == "We build the thing. Then we ship it."
    assert paragraphs[0].start_ms == 0


def test_breaks_on_long_pause():
    segments = [_seg("First topic.", 0), _seg("Different topic.", 10_000)]
    paragraphs = build_paragraphs(segments)
    assert len(paragraphs) == 2
    assert paragraphs[1].start_ms == 10_000
    assert paragraphs[1].index == 1


def test_does_not_break_on_short_pause():
    segments = [_seg("Keep going.", 0), _seg("Still the same idea.", 1500)]
    assert len(build_paragraphs(segments)) == 1


def test_breaks_at_sentence_boundary_after_word_limit():
    segments = [_seg(f"word{i} sentence ends here.", i * 1000) for i in range(40)]
    paragraphs = build_paragraphs(segments, max_words=20)
    assert len(paragraphs) > 1
    # 每段都应结束在句末标点上，不能把句子劈开
    assert all(p.text.rstrip().endswith(".") for p in paragraphs)


def test_hard_cap_applies_when_captions_have_no_punctuation():
    """无标点的自动字幕不能产出一个巨型段落。"""
    segments = [_seg("no punctuation here at all", i * 500) for i in range(100)]
    paragraphs = build_paragraphs(segments, max_words=20)
    assert len(paragraphs) > 1
    assert all(len(p.text.split()) <= 20 * 2 + 10 for p in paragraphs)


def test_preserves_timestamps_from_first_segment_of_paragraph():
    segments = [_seg("A.", 5000), _seg("B.", 6000), _seg("C.", 30_000)]
    paragraphs = build_paragraphs(segments)
    assert [p.start_ms for p in paragraphs] == [5000, 30_000]


def test_handles_segments_without_timestamps():
    segments = [Segment(text="Plain one."), Segment(text="Plain two.")]
    paragraphs = build_paragraphs(segments)
    assert len(paragraphs) == 1
    assert paragraphs[0].start_ms is None


def test_empty_input_returns_empty():
    assert build_paragraphs([]) == []
