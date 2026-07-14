"""Metadata dump: CSV of unique tracks found on Spotify, with genres/tags flattened."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from supernatural_soundtrack_scraper.spotify_enrichment.config import load_enrichment_config

DUMP_COLUMNS = [
    "song",
    "artist",
    "spotify_track_name",
    "spotify_artist_name",
    "album_name",
    "album_release_date",
    "release_year",
    "genres",
    "tags",
    "duration_ms",
    "match_confidence",
    "spotify_track_id",
    "spotify_uri",
    "artist_id",
    "album_id",
]


def build_dump_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filter enrichment records to spotify_present=true, dedupe by track id
    (first occurrence wins, so input order is preserved), flatten genres/tags
    into "; "-joined strings.
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rec in records:
        if not rec.get("spotify_present"):
            continue
        key = rec.get("spotify_track_id") or f"{rec.get('song', '')}|{rec.get('artist', '')}"
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "song": rec.get("song", ""),
                "artist": rec.get("artist", ""),
                "spotify_track_name": rec.get("spotify_track_name", ""),
                "spotify_artist_name": rec.get("spotify_artist_name", ""),
                "album_name": rec.get("album_name", ""),
                "album_release_date": rec.get("album_release_date", ""),
                "release_year": rec.get("release_year", ""),
                "genres": "; ".join(rec.get("genres") or []),
                "tags": "; ".join(rec.get("tags") or []),
                "duration_ms": rec.get("duration_ms", 0),
                "match_confidence": rec.get("match_confidence", 0.0),
                "spotify_track_id": rec.get("spotify_track_id", ""),
                "spotify_uri": rec.get("spotify_uri", ""),
                "artist_id": rec.get("artist_id", ""),
                "album_id": rec.get("album_id", ""),
            }
        )
    return rows


def dump_metadata(json_path: str, output_csv: str) -> str:
    """
    Write the metadata dump CSV from the enrichment JSON (temp then replace).
    Returns the output CSV path.
    """
    if not json_path or not os.path.isfile(json_path):
        raise FileNotFoundError(
            f"Enrichment JSON not found: {json_path}. Run `poetry run enrich` first."
        )
    if not output_csv:
        raise ValueError("METADATA_CSV must be set")

    with open(json_path) as f:
        data = json.load(f)
    records = list(data) if isinstance(data, list) else []
    rows = build_dump_rows(records)

    out_dir = str(Path(output_csv).parent)
    tmp_csv = os.path.join(out_dir, Path(output_csv).name + ".tmp")
    with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DUMP_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    os.replace(tmp_csv, output_csv)
    return output_csv


def main() -> None:
    """CLI entry point for the dump script."""
    config = load_enrichment_config()
    out = dump_metadata(config["output_json"], config["metadata_csv"])
    print(f"Metadata dump done: {out}")
