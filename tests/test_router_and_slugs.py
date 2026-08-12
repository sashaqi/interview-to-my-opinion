"""输入分类与文件名生成测试。"""

from __future__ import annotations

import pytest

from itmo.fetch.router import SourceRouterError, SourceType, detect_source
from itmo.slugs import interview_filename, interview_note_name, note_title, slugify


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc123",
        "https://youtu.be/abc123",
        "https://m.youtube.com/watch?v=abc123",
        "https://music.youtube.com/watch?v=abc123",
    ],
)
def test_detects_youtube_urls(url):
    assert detect_source(url).type is SourceType.YOUTUBE


def test_detects_apple_podcast_url():
    url = "https://podcasts.apple.com/us/podcast/some-show/id123"
    assert detect_source(url).type is SourceType.APPLE_PODCAST


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/feed.xml",
        "https://example.com/podcast/rss",
        "https://example.com/feed/",
    ],
)
def test_detects_podcast_rss(url):
    assert detect_source(url).type is SourceType.PODCAST_RSS


@pytest.mark.parametrize("path", ["notes.txt", "~/talk.srt", "a/b/c.vtt", "x.json3", "y.md"])
def test_detects_local_transcript_paths(path):
    assert detect_source(path).type is SourceType.LOCAL_TRANSCRIPT


def test_rejects_empty_input():
    with pytest.raises(SourceRouterError):
        detect_source("   ")


def test_rejects_unknown_url_and_mentions_escape_hatch():
    with pytest.raises(SourceRouterError, match="transcript-file"):
        detect_source("https://example.com/some/article")


def test_rejects_unsupported_local_extension():
    with pytest.raises(SourceRouterError):
        detect_source("audio.mp3")


def test_slugify_strips_filesystem_and_wikilink_hostile_characters():
    assert slugify('AI: the "next" [big] thing?') == "AI-the-next-big-thing"


def test_slugify_preserves_chinese():
    assert slugify("观点 提炼 测试") == "观点-提炼-测试"


def test_slugify_truncates_at_word_boundary():
    result = slugify("alpha beta gamma delta epsilon zeta eta theta", max_length=20)
    assert len(result) <= 20
    assert not result.endswith("-")


def test_slugify_falls_back_when_everything_is_stripped():
    assert slugify("///") == "untitled"


def test_interview_filename_prefixes_valid_date():
    assert interview_filename("2026-08-12", "My Talk") == "2026-08-12-My-Talk"


def test_interview_filename_omits_invalid_date():
    assert interview_filename("", "My Talk") == "My-Talk"
    assert interview_filename("20260812", "My Talk") == "My-Talk"


def test_note_title_keeps_spaces_for_wikilink_compatibility():
    assert note_title("Evaluation is the hidden cost") == "Evaluation is the hidden cost"


def test_note_title_strips_only_wikilink_and_filesystem_hostile_chars():
    """逗号、括号 Obsidian 能处理，保留；[] # ^ | 会破坏链接，剔除。"""
    assert note_title("A claim, with (parens)") == "A claim, with (parens)"
    assert note_title("Why #1 [x] ^y | z") == "Why 1 x y z"
    assert note_title("path/to: thing") == "path to thing"


def test_note_title_truncates_at_word_boundary():
    result = note_title("alpha beta gamma delta epsilon zeta", max_length=20)
    assert len(result) <= 20
    assert not result.endswith(" ")


def test_note_title_falls_back_when_everything_is_stripped():
    assert note_title("###") == "untitled"


def test_interview_note_name_uses_readable_form():
    assert interview_note_name("2026-08-12", "My Talk") == "2026-08-12 My Talk"
    assert interview_note_name("", "My Talk") == "My Talk"
