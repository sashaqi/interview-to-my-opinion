"""播客文字稿采集测试。

多数播客没有文字稿，所以「失败时给出可行的下一步」和成功路径同样重要。
"""

from __future__ import annotations

import pytest

from itmo.fetch.podcast import PodcastFetchError, _find_transcript_link, _pick_episode


class _Feed:
    def __init__(self, entries, bozo=False):
        self.entries = entries
        self.bozo = bozo


def test_picks_latest_episode_by_default():
    feed = _Feed([{"title": "Newest"}, {"title": "Older"}])
    assert _pick_episode(feed, None)["title"] == "Newest"


def test_picks_episode_by_title_keyword():
    feed = _Feed([{"title": "Ep 10 Bottlenecks"}, {"title": "Ep 9 Verifiability"}])
    assert _pick_episode(feed, "verifiability")["title"] == "Ep 9 Verifiability"


def test_unmatched_episode_lists_available_titles():
    feed = _Feed([{"title": "Ep 10 Bottlenecks"}])
    with pytest.raises(PodcastFetchError, match="Ep 10 Bottlenecks"):
        _pick_episode(feed, "nonexistent")


def test_empty_feed_is_reported():
    with pytest.raises(PodcastFetchError, match="没有任何单集"):
        _pick_episode(_Feed([]), None)


def test_finds_transcript_from_podcast_namespace_tag():
    entry = {
        "podcast_transcript": {"url": "https://e.com/t.vtt", "type": "text/vtt"},
        "links": [],
    }
    assert _find_transcript_link(entry) == ("https://e.com/t.vtt", "text/vtt")


def test_finds_transcript_when_tag_is_a_list():
    entry = {
        "podcast_transcript": [
            {"url": "https://e.com/t.html", "type": "text/html"},
            {"url": "https://e.com/t.srt", "type": "application/x-subrip"},
        ],
        "links": [],
    }
    assert _find_transcript_link(entry)[1] == "application/x-subrip"


def test_finds_transcript_from_link_rel():
    entry = {"links": [{"href": "https://e.com/t.vtt", "rel": "transcript", "type": "text/vtt"}]}
    assert _find_transcript_link(entry) == ("https://e.com/t.vtt", "text/vtt")


def test_missing_transcript_points_at_the_escape_hatch():
    with pytest.raises(PodcastFetchError, match="--transcript-file"):
        _find_transcript_link({"links": []})


def test_unsupported_transcript_format_is_distinguished_from_missing():
    """有文字稿但格式不支持，和完全没有文字稿，用户的下一步不一样。"""
    entry = {"podcast_transcript": {"url": "https://e.com/t.html", "type": "text/html"}}
    with pytest.raises(PodcastFetchError, match="text/html"):
        _find_transcript_link(entry)
