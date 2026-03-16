"""Tests for Spotify enrichment: models, config, presence matcher, taxonomy tagger, enricher."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from spotipy.exceptions import SpotifyException

from supernatural_soundtrack_scraper.spotify_enrichment.config import (
    load_enrichment_config,
    load_taxonomy,
)
from supernatural_soundtrack_scraper.spotify_enrichment.enricher import (
    _build_lookup,
    _load_existing_json,
    _load_input_csv,
    run_enrichment,
)
from supernatural_soundtrack_scraper.spotify_enrichment.models import (
    EnrichedRecord,
    SoundtrackInputRow,
)
from supernatural_soundtrack_scraper.spotify_enrichment.presence_matcher import match_track
from supernatural_soundtrack_scraper.spotify_enrichment.taxonomy_tagger import tag_track


# --- Models ---


def test_soundtrack_input_row_from_csv_row_full() -> None:
    row = {
        "season": 1,
        "episode_code": "01x01",
        "episode_title": "Pilot",
        "overall_episode": 1,
        "song": "Back In Black",
        "artist": "AC/DC",
        "note": "",
        "source_url": "https://example.com",
        "source_api_url": "https://api.example.com",
    }
    r = SoundtrackInputRow.from_csv_row(row)
    assert r.season == 1
    assert r.episode_code == "01x01"
    assert r.song == "Back In Black"
    assert r.artist == "AC/DC"
    assert r.note == ""
    assert r.lookup_key() == ("back in black", "ac/dc")


def test_soundtrack_input_row_from_csv_row_missing_optionals() -> None:
    row = {
        "season": 2,
        "episode_code": "02x03",
        "episode_title": "X",
        "overall_episode": 5,
        "song": "Song",
        "artist": "Artist",
    }
    r = SoundtrackInputRow.from_csv_row(row)
    assert r.note == ""
    assert r.source_url == ""
    assert r.source_api_url == ""


def test_soundtrack_input_row_lookup_key_normalizes_whitespace() -> None:
    r = SoundtrackInputRow(
        season=1,
        episode_code="01x01",
        episode_title="Pilot",
        overall_episode=1,
        song="  Highway  to   Hell  ",
        artist="  AC/DC  ",
    )
    assert r.lookup_key() == ("highway to hell", "ac/dc")


def test_enriched_record_to_csv_row_omits_genres_tags_tag_source() -> None:
    rec = EnrichedRecord(
        season=1,
        episode_code="01x01",
        episode_title="Pilot",
        overall_episode=1,
        song="S",
        artist="A",
        genres=["rock"],
        tags=["driving"],
        tag_source="hybrid",
    )
    row = rec.to_csv_row()
    assert "genres" not in row
    assert "tags" not in row
    assert "tag_source" not in row
    assert row["season"] == 1
    assert row["spotify_present"] is False


def test_enriched_record_to_csv_row_has_all_scalar_columns() -> None:
    rec = EnrichedRecord(
        season=1,
        episode_code="01x01",
        episode_title="P",
        overall_episode=1,
        song="S",
        artist="A",
        spotify_track_id="abc",
        release_year="1980",
    )
    keys = list(rec.to_csv_row().keys())
    assert "last_updated" in keys
    assert "album_name" in keys
    assert len(keys) == 20


# --- Config ---


def test_load_enrichment_config_returns_expected_keys() -> None:
    config = load_enrichment_config()
    assert "input_csv" in config
    assert "output_json" in config
    assert "output_csv" in config
    assert "taxonomy_path" in config
    assert "spotify_client_id" in config
    assert "spotify_client_secret" in config


def test_load_enrichment_config_resolves_relative_paths() -> None:
    config = load_enrichment_config()
    root = Path(__file__).resolve().parent.parent
    if config["input_csv"]:
        assert Path(config["input_csv"]).is_absolute()
    if config["taxonomy_path"]:
        assert Path(config["taxonomy_path"]).is_absolute()
        assert "config" in config["taxonomy_path"] and "taxonomy" in config["taxonomy_path"]


def test_load_taxonomy_valid_file() -> None:
    root = Path(__file__).resolve().parent.parent
    path = root / "config" / "taxonomy.yaml"
    if not path.exists():
        pytest.skip("config/taxonomy.yaml not found")
    tax = load_taxonomy(str(path))
    assert "genres" in tax or "moods" in tax or "mood_rules" in tax


def test_load_taxonomy_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_taxonomy("/nonexistent/taxonomy.yaml")


def test_load_taxonomy_empty_file_returns_empty_dict() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        path = f.name
    try:
        tax = load_taxonomy(path)
        assert tax == {} or tax is not None
    finally:
        os.unlink(path)


# --- Presence matcher (mocked Spotify) ---


def test_match_track_empty_song_returns_not_present() -> None:
    sp = MagicMock()
    result = match_track(sp, "", "Artist")
    assert result["spotify_present"] is False
    assert result["spotify_track_id"] == ""
    sp.search.assert_not_called()


def test_match_track_empty_artist_returns_not_present() -> None:
    sp = MagicMock()
    result = match_track(sp, "Song", "")
    assert result["spotify_present"] is False
    sp.search.assert_not_called()


def test_match_track_api_exception_returns_not_present() -> None:
    sp = MagicMock()
    sp.search.side_effect = Exception("rate limit")
    result = match_track(sp, "Song", "Artist")
    assert result["spotify_present"] is False
    assert result["spotify_track_id"] == ""


def test_match_track_empty_items_returns_not_present() -> None:
    sp = MagicMock()
    sp.search.return_value = {"tracks": {"items": []}}
    result = match_track(sp, "Song", "Artist")
    assert result["spotify_present"] is False


def test_match_track_no_tracks_key_returns_not_present() -> None:
    sp = MagicMock()
    sp.search.return_value = {}
    result = match_track(sp, "Song", "Artist")
    assert result["spotify_present"] is False


def test_match_track_valid_response_parses_fields() -> None:
    sp = MagicMock()
    sp.search.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "tid123",
                    "uri": "spotify:track:tid123",
                    "duration_ms": 255000,
                    "artists": [{"id": "aid456", "name": "AC/DC"}],
                    "album": {
                        "id": "albid",
                        "name": "Back In Black",
                        "release_date": "1980-07-25",
                    },
                },
            ],
        },
    }
    result = match_track(sp, "Back In Black", "AC/DC")
    assert result["spotify_present"] is True
    assert result["spotify_track_id"] == "tid123"
    assert result["spotify_uri"] == "spotify:track:tid123"
    assert result["artist_id"] == "aid456"
    assert result["album_name"] == "Back In Black"
    assert result["album_release_date"] == "1980-07-25"
    assert result["release_year"] == "1980"
    assert result["duration_ms"] == 255000
    assert result["match_confidence"] == 1.0


def test_match_track_release_date_year_only() -> None:
    sp = MagicMock()
    sp.search.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "tid",
                    "uri": "spotify:track:tid",
                    "duration_ms": 0,
                    "artists": [{"id": "a", "name": "Artist"}],
                    "album": {"id": "al", "name": "Album", "release_date": "1992"},
                },
            ],
        },
    }
    result = match_track(sp, "S", "Artist")
    assert result["release_year"] == "1992"


def test_match_track_spotify_403_premium_raises_runtime_error() -> None:
    sp = MagicMock()
    exc = SpotifyException(
        http_status=403,
        code=-1,
        msg="Active premium subscription required for the owner of the app. When the subscription status changes, it can take a few hours before requests are allowed again.",
    )
    sp.search.side_effect = exc
    with pytest.raises(RuntimeError):
        match_track(sp, "Escort Service", "David Mann and Emanuel Kallins")


def test_match_track_spotify_500_logs_and_returns_not_present(monkeypatch) -> None:
    sp = MagicMock()
    exc = SpotifyException(
        http_status=500,
        code=-1,
        msg="Internal server error",
    )
    sp.search.side_effect = exc

    printed: list[str] = []

    def fake_print(*args: object, **kwargs: object) -> None:
        if args:
            printed.append(str(args[0]))

    monkeypatch.setattr("builtins.print", fake_print)
    result = match_track(sp, "Song", "Artist")
    assert result["spotify_present"] is False
    assert any("Spotify API error (500)" in m for m in printed)


# --- Taxonomy tagger (mocked Spotify) ---


def test_tag_track_empty_track_and_artist_id_returns_empty() -> None:
    sp = MagicMock()
    taxonomy = {"genres": ["rock"], "moods": ["sad"], "mood_rules": {}}
    genres, tags, source = tag_track(sp, "", "", taxonomy)
    assert genres == []
    assert tags == []
    assert source == ""
    sp.artist.assert_not_called()
    sp.audio_features.assert_not_called()


def test_tag_track_taxonomy_empty_genres_moods_returns_empty_tags() -> None:
    sp = MagicMock()
    sp.artist.return_value = {"genres": ["rock"]}
    sp.audio_features.return_value = [{}]
    taxonomy: dict = {}
    genres, tags, source = tag_track(sp, "tid", "aid", taxonomy)
    assert tags == []
    assert source == ""


def test_tag_track_artist_api_exception_returns_empty_genres() -> None:
    sp = MagicMock()
    sp.artist.side_effect = Exception("not found")
    sp.audio_features.return_value = [{"energy": 0.5}]
    taxonomy = {"genres": ["rock"], "moods": [], "mood_rules": {}}
    genres, tags, source = tag_track(sp, "tid", "aid", taxonomy)
    assert genres == []
    assert "rock" not in tags


def test_tag_track_audio_features_api_exception_uses_empty_features() -> None:
    sp = MagicMock()
    sp.artist.return_value = {"genres": ["rock"]}
    sp.audio_features.side_effect = Exception("error")
    taxonomy = {"genres": ["rock"], "moods": ["party"], "mood_rules": {"party": {"energy_min": 0.1}}}
    genres, tags, source = tag_track(sp, "tid", "aid", taxonomy)
    assert "rock" in genres
    assert "rock" in tags
    assert source == "spotify_genres"
    assert "party" not in tags


def test_tag_track_genre_substring_match_adds_tag() -> None:
    sp = MagicMock()
    sp.artist.return_value = {"genres": ["classic rock", "hard rock"]}
    sp.audio_features.return_value = [None]
    taxonomy = {"genres": ["rock", "classic_rock"], "moods": [], "mood_rules": {}}
    genres, tags, source = tag_track(sp, "tid", "aid", taxonomy)
    assert "classic rock" in genres
    assert "rock" in tags or "classic_rock" in tags
    assert source != ""


def test_tag_track_mood_rule_satisfied_adds_tag() -> None:
    sp = MagicMock()
    sp.artist.return_value = {"genres": []}
    sp.audio_features.return_value = [
        {"energy": 0.8, "valence": 0.2, "danceability": 0.6, "tempo": 120, "acousticness": 0.1},
    ]
    taxonomy = {
        "genres": [],
        "moods": ["party"],
        "mood_rules": {"party": {"energy_min": 0.7, "danceability_min": 0.5}},
    }
    genres, tags, source = tag_track(sp, "tid", "aid", taxonomy)
    assert "party" in tags
    assert source == "spotify_audio_features"


def test_tag_track_mood_rule_not_satisfied_omits_tag() -> None:
    sp = MagicMock()
    sp.artist.return_value = {"genres": []}
    sp.audio_features.return_value = [
        {"energy": 0.3, "valence": 0.2, "danceability": 0.2, "tempo": 80, "acousticness": 0.5},
    ]
    taxonomy = {
        "genres": [],
        "moods": ["party"],
        "mood_rules": {"party": {"energy_min": 0.7, "danceability_min": 0.5}},
    }
    genres, tags, source = tag_track(sp, "tid", "aid", taxonomy)
    assert "party" not in tags


# --- Enricher helpers ---


def test_load_input_csv_valid() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(
            "season,episode_code,episode_title,overall_episode,song,artist,note,source_url,source_api_url\n"
            "1,01x01,Pilot,1,Back In Black,AC/DC,,,\n"
        )
        path = f.name
    try:
        rows = _load_input_csv(path)
        assert len(rows) == 1
        assert rows[0].song == "Back In Black"
        assert rows[0].artist == "AC/DC"
    finally:
        os.unlink(path)


def test_load_input_csv_empty_returns_empty_list() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(
            "season,episode_code,episode_title,overall_episode,song,artist,note,source_url,source_api_url\n"
        )
        path = f.name
    try:
        rows = _load_input_csv(path)
        assert rows == []
    finally:
        os.unlink(path)


def test_load_existing_json_missing_file_returns_empty_list() -> None:
    assert _load_existing_json("/nonexistent/path.json") == []


def test_load_existing_json_invalid_json_returns_empty_list() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {")
        path = f.name
    try:
        assert _load_existing_json(path) == []
    finally:
        os.unlink(path)


def test_load_existing_json_valid_array_returns_list() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump([{"song": "S", "artist": "A", "spotify_present": True}], f)
        path = f.name
    try:
        data = _load_existing_json(path)
        assert len(data) == 1
        assert data[0]["spotify_present"] is True
    finally:
        os.unlink(path)


def test_build_lookup_empty_returns_empty_dict() -> None:
    assert _build_lookup([]) == {}


def test_build_lookup_ignores_records_without_spotify_fields() -> None:
    records = [
        {"song": "S", "artist": "A"},
    ]
    lookup = _build_lookup(records)
    assert lookup == {}


def test_build_lookup_includes_record_with_spotify_present_false() -> None:
    records = [
        {"song": "S", "artist": "A", "spotify_present": False},
    ]
    lookup = _build_lookup(records)
    assert ("s", "a") in lookup
    assert lookup[("s", "a")]["spotify_present"] is False


def test_build_lookup_deduplicates_by_normalized_key() -> None:
    records = [
        {"song": "Song", "artist": "Artist", "spotify_present": True, "spotify_track_id": "t1"},
        {"song": "  song  ", "artist": "  ARTIST  ", "spotify_present": True, "spotify_track_id": "t2"},
    ]
    lookup = _build_lookup(records)
    assert len(lookup) == 1
    key = ("song", "artist")
    assert key in lookup
    assert lookup[key]["spotify_track_id"] in ("t1", "t2")


# --- run_enrichment negative flows ---


def test_run_enrichment_missing_credentials_raises() -> None:
    with patch.dict(os.environ, {"SPOTIFY_CLIENT_ID": "", "SPOTIFY_CLIENT_SECRET": ""}, clear=False):
        with pytest.raises(ValueError, match="SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET"):
            run_enrichment()


def test_run_enrichment_missing_input_csv_raises() -> None:
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        input_csv = Path(tmp) / "nonexistent.csv"
        output_json = Path(tmp) / "out.json"
        output_csv = Path(tmp) / "out.csv"
        taxonomy_path = root / "config" / "taxonomy.yaml"
        if not taxonomy_path.exists():
            pytest.skip("config/taxonomy.yaml not found")
        env = {
            "SPOTIFY_CLIENT_ID": "id",
            "SPOTIFY_CLIENT_SECRET": "secret",
            "INPUT_CSV": str(input_csv),
            "OUTPUT_JSON": str(output_json),
            "OUTPUT_CSV": str(output_csv),
            "TAXONOMY_PATH": str(taxonomy_path),
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(FileNotFoundError, match="Input CSV not found"):
                run_enrichment()


def test_run_enrichment_missing_taxonomy_raises() -> None:
    root = Path(__file__).resolve().parent.parent
    input_csv = root / "supernatural_complete_soundtrack.csv"
    if not input_csv.exists():
        input_csv = root / "supernatural_soundtrack.csv"
    if not input_csv.exists():
        pytest.skip("no soundtrack CSV in repo")
    with tempfile.TemporaryDirectory() as tmp:
        output_json = Path(tmp) / "out.json"
        output_csv = Path(tmp) / "out.csv"
        taxonomy_path = Path(tmp) / "missing_taxonomy.yaml"
        env = {
            "SPOTIFY_CLIENT_ID": "id",
            "SPOTIFY_CLIENT_SECRET": "secret",
            "INPUT_CSV": str(input_csv),
            "OUTPUT_JSON": str(output_json),
            "OUTPUT_CSV": str(output_csv),
            "TAXONOMY_PATH": str(taxonomy_path),
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(FileNotFoundError, match="Taxonomy not found"):
                run_enrichment()


def test_run_enrichment_success_with_mocked_spotify() -> None:
    root = Path(__file__).resolve().parent.parent
    taxonomy_path = root / "config" / "taxonomy.yaml"
    if not taxonomy_path.exists():
        pytest.skip("config/taxonomy.yaml not found")

    with tempfile.TemporaryDirectory() as tmp:
        input_csv = Path(tmp) / "input.csv"
        pd.DataFrame([
            {
                "season": 1,
                "episode_code": "01x01",
                "episode_title": "Pilot",
                "overall_episode": 1,
                "song": "Back In Black",
                "artist": "AC/DC",
                "note": "",
                "source_url": "",
                "source_api_url": "",
            },
        ]).to_csv(input_csv, index=False)

        output_json = Path(tmp) / "out.json"
        output_csv = Path(tmp) / "out.csv"
        env = {
            "SPOTIFY_CLIENT_ID": "test_id",
            "SPOTIFY_CLIENT_SECRET": "test_secret",
            "INPUT_CSV": str(input_csv),
            "OUTPUT_JSON": str(output_json),
            "OUTPUT_CSV": str(output_csv),
            "TAXONOMY_PATH": str(taxonomy_path),
        }
        mock_sp = MagicMock()
        mock_sp.search.return_value = {
            "tracks": {
                "items": [
                    {
                        "id": "tid",
                        "uri": "spotify:track:tid",
                        "duration_ms": 255000,
                        "artists": [{"id": "aid", "name": "AC/DC"}],
                        "album": {"id": "alid", "name": "Back In Black", "release_date": "1980"},
                    },
                ],
            },
        }
        mock_sp.artist.return_value = {"genres": ["rock"]}
        mock_sp.audio_features.return_value = [{"energy": 0.5, "valence": 0.5, "danceability": 0.4, "tempo": 100, "acousticness": 0.2}]

        with patch.dict(os.environ, env, clear=False):
            with patch(
                "supernatural_soundtrack_scraper.spotify_enrichment.enricher.create_spotify_client",
                return_value=mock_sp,
            ):
                out_json, out_csv = run_enrichment()
        assert Path(out_json).exists()
        assert Path(out_csv).exists()
        with open(output_json) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["song"] == "Back In Black"
        assert data[0]["spotify_present"] is True
        assert "genres" in data[0]
        assert "tags" in data[0]
        csv_content = Path(output_csv).read_text()
        assert "Back In Black" in csv_content
        assert "spotify_present" in csv_content
        assert "genres" not in csv_content
