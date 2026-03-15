"""Tests for core scraping logic."""

from __future__ import annotations

import pytest

from supernatural_soundtrack_scraper.core import SongRow, parse_songs


def test_parse_songs_returns_list_of_song_row() -> None:
    fixture = '''
== Season 1 ==
* "Carry On Wayward Son" – Kansas
* "Bad Moon Rising" – Creedence Clearwater Revival
'''
    rows = parse_songs(fixture)
    assert len(rows) == 2
    assert rows[0].season == 1
    assert rows[0].song == "Carry On Wayward Son"
    assert rows[0].artist == "Kansas"
    assert rows[1].season == 1
    assert rows[1].song == "Bad Moon Rising"
    assert rows[1].artist == "Creedence Clearwater Revival"


def test_parse_songs_multiple_seasons() -> None:
    fixture = '''
== Season 1 ==
* "Song A" – Artist A
== Season 2 ==
* "Song B" – Artist B
'''
    rows = parse_songs(fixture)
    assert len(rows) == 2
    assert rows[0].season == 1 and rows[0].song == "Song A"
    assert rows[1].season == 2 and rows[1].song == "Song B"


def test_song_row_model() -> None:
    row = SongRow(season=1, song="Test Song", artist="Test Artist")
    assert row.season == 1
    assert row.song == "Test Song"
    assert row.artist == "Test Artist"
    assert row.model_dump() == {"season": 1, "song": "Test Song", "artist": "Test Artist"}
