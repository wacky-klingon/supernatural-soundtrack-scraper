"""Pydantic models for Spotify enrichment I/O."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


def _normalize_key(s: str) -> str:
    return " ".join(s.strip().lower().split()) if s else ""


class SoundtrackInputRow(BaseModel):
    """One row from the source soundtrack CSV."""

    season: int
    episode_code: str
    episode_title: str
    overall_episode: int
    song: str
    artist: str
    note: str = ""
    source_url: str = ""
    source_api_url: str = ""

    def lookup_key(self) -> tuple[str, str]:
        """Normalized (song, artist) for idempotent lookup."""
        return (_normalize_key(self.song), _normalize_key(self.artist))

    @classmethod
    def from_csv_row(cls, row: dict[str, Any]) -> "SoundtrackInputRow":
        """Build from a CSV row (e.g. from pandas or csv.DictReader)."""
        return cls(
            season=int(row["season"]),
            episode_code=str(row["episode_code"]),
            episode_title=str(row["episode_title"]),
            overall_episode=int(row["overall_episode"]),
            song=str(row["song"]),
            artist=str(row["artist"]),
            note=str(row.get("note", "") or ""),
            source_url=str(row.get("source_url", "") or ""),
            source_api_url=str(row.get("source_api_url", "") or ""),
        )


class EnrichedRecord(BaseModel):
    """Full enriched record (JSON source of truth shape)."""

    # Input columns (passthrough)
    season: int
    episode_code: str
    episode_title: str
    overall_episode: int
    song: str
    artist: str
    note: str = ""
    source_url: str = ""
    source_api_url: str = ""

    # Step 2: presence + track/album/artist
    spotify_present: bool = False
    spotify_track_id: str = ""
    spotify_uri: str = ""
    match_confidence: float = 0.0
    album_id: str = ""
    album_name: str = ""
    album_release_date: str = ""
    release_year: str = ""
    artist_id: str = ""
    duration_ms: int = 0

    # Step 3: taxonomy
    genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    tag_source: str = ""

    # Enricher
    last_updated: str = ""

    def to_csv_row(self) -> dict[str, Any]:
        """Scalar columns only for derived CSV (no genres, tags, tag_source)."""
        return {
            "season": self.season,
            "episode_code": self.episode_code,
            "episode_title": self.episode_title,
            "overall_episode": self.overall_episode,
            "song": self.song,
            "artist": self.artist,
            "note": self.note,
            "source_url": self.source_url,
            "source_api_url": self.source_api_url,
            "spotify_present": self.spotify_present,
            "spotify_track_id": self.spotify_track_id,
            "spotify_uri": self.spotify_uri,
            "match_confidence": self.match_confidence,
            "album_id": self.album_id,
            "album_name": self.album_name,
            "album_release_date": self.album_release_date,
            "release_year": self.release_year,
            "artist_id": self.artist_id,
            "duration_ms": self.duration_ms,
            "last_updated": self.last_updated,
        }
