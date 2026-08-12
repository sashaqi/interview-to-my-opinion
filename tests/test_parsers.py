"""字幕解析测试。重点覆盖自动字幕的滚动重复去重。"""

from __future__ import annotations

import json

import pytest

from itmo.transcript.parsers import (
    TranscriptParseError,
    parse_json3,
    parse_plain_text,
    parse_srt,
    parse_vtt,
)


def _json3(events: list[dict]) -> str:
    return json.dumps({"wireMagic": "pb3", "events": events})


def test_parse_json3_extracts_text_and_timing():
    content = _json3(
        [
            {"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "We need to "}, {"utf8": "ship."}]},
            {"tStartMs": 3000, "dDurationMs": 1500, "segs": [{"utf8": "That is the point."}]},
        ]
    )
    segments = parse_json3(content)
    assert [s.text for s in segments] == ["We need to ship.", "That is the point."]
    assert segments[0].start_ms == 1000
    assert segments[0].duration_ms == 2000


def test_parse_json3_drops_sound_tags_and_empty_events():
    content = _json3(
        [
            {"tStartMs": 0, "segs": [{"utf8": "[♪♪♪]"}]},
            {"tStartMs": 500, "segs": [{"utf8": "  "}]},
            {"tStartMs": 1000},
            {"tStartMs": 1500, "segs": [{"utf8": "Real content."}]},
        ]
    )
    assert [s.text for s in parse_json3(content)] == ["Real content."]


def test_parse_json3_dedupes_rolling_autocaptions():
    """自动字幕逐词重发同一句，只应保留最完整的那条。"""
    content = _json3(
        [
            {"tStartMs": 0, "segs": [{"utf8": "the model"}]},
            {"tStartMs": 300, "segs": [{"utf8": "the model just"}]},
            {"tStartMs": 600, "segs": [{"utf8": "the model just works"}]},
            {"tStartMs": 2000, "segs": [{"utf8": "and that changes things"}]},
        ]
    )
    assert [s.text for s in parse_json3(content)] == [
        "the model just works",
        "and that changes things",
    ]


def test_parse_json3_skips_append_frames():
    content = _json3(
        [
            {"tStartMs": 0, "segs": [{"utf8": "First line."}]},
            {"tStartMs": 100, "aAppend": 1, "segs": [{"utf8": "\n"}]},
            {"tStartMs": 200, "segs": [{"utf8": "Second line."}]},
        ]
    )
    assert [s.text for s in parse_json3(content)] == ["First line.", "Second line."]


def test_parse_json3_rejects_malformed_payload():
    with pytest.raises(TranscriptParseError):
        parse_json3("not json at all")
    with pytest.raises(TranscriptParseError):
        parse_json3(json.dumps({"wireMagic": "pb3"}))


def test_parse_vtt_reads_cues_and_strips_tags():
    content = """WEBVTT

00:00:01.000 --> 00:00:03.500
<c.colorE5E5E5>Leverage</c> compounds.

00:00:04.000 --> 00:00:06.000
That is the whole idea.
"""
    segments = parse_vtt(content)
    assert [s.text for s in segments] == ["Leverage compounds.", "That is the whole idea."]
    assert segments[0].start_ms == 1000
    assert segments[0].duration_ms == 2500


def test_parse_srt_reads_numbered_cues():
    content = """1
00:00:02,000 --> 00:00:04,000
The market rewards patience.

2
00:00:05,000 --> 00:00:07,000
Most people cannot wait.
"""
    segments = parse_srt(content)
    assert [s.text for s in segments] == [
        "The market rewards patience.",
        "Most people cannot wait.",
    ]
    assert segments[0].start_ms == 2000


def test_parse_srt_rejects_content_without_timing():
    with pytest.raises(TranscriptParseError):
        parse_srt("just some prose with no timecodes")


def test_parse_plain_text_splits_on_blank_lines():
    segments = parse_plain_text("First idea.\n\nSecond idea.\n\n\nThird idea.")
    assert [s.text for s in segments] == ["First idea.", "Second idea.", "Third idea."]
    assert all(s.start_ms is None for s in segments)


def test_parse_plain_text_falls_back_to_line_split():
    segments = parse_plain_text("Line one.\nLine two.")
    assert [s.text for s in segments] == ["Line one.", "Line two."]


def test_parse_plain_text_rejects_empty():
    with pytest.raises(TranscriptParseError):
        parse_plain_text("   \n  \n ")
