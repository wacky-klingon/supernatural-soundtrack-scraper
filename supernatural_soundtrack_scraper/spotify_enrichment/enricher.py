"""Orchestrator: load input, resume from JSON, match + tag, write JSON and derived CSV."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from supernatural_soundtrack_scraper.spotify_enrichment.config import (
    load_enrichment_config,
    load_taxonomy,
)
from supernatural_soundtrack_scraper.spotify_enrichment.models import (
    EnrichedRecord,
    SoundtrackInputRow,
)
from supernatural_soundtrack_scraper.spotify_enrichment.presence_matcher import (
    create_spotify_client,
    match_track,
)
from supernatural_soundtrack_scraper.spotify_enrichment.taxonomy_tagger import tag_track


def _load_input_csv(path: str) -> list[SoundtrackInputRow]:
    """Load soundtrack CSV into SoundtrackInputRow list."""
    df = pd.read_csv(path)
    return [SoundtrackInputRow.from_csv_row(row) for _, row in df.iterrows()]


def _load_existing_json(path: str) -> list[dict[str, Any]]:
    """Load existing output JSON; return list of record dicts or [] if missing/invalid."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return list(data) if isinstance(data, list) else []
    except Exception:
        return []


def _build_lookup(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Build (song_norm, artist_norm) -> full record dict from existing JSON records."""
    key_fn = lambda r: (
        " ".join((r.get("song") or "").strip().lower().split()),
        " ".join((r.get("artist") or "").strip().lower().split()),
    )
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in records:
        if rec.get("spotify_present") is not None or rec.get("spotify_track_id") is not None:
            lookup[key_fn(rec)] = rec
    return lookup


def _record_to_dict(rec: EnrichedRecord) -> dict[str, Any]:
    """Serialize EnrichedRecord for JSON (lists stay as lists)."""
    d = rec.model_dump()
    return d


def run_enrichment() -> tuple[str, str]:
    """
    Load input CSV and optional existing JSON; enrich only new (song, artist);
    write JSON (temp then replace) and derive CSV (temp then replace).
    Returns (output_json_path, output_csv_path).
    """
    config = load_enrichment_config()
    input_csv = config["input_csv"]
    output_json = config["output_json"]
    output_csv = config["output_csv"]
    taxonomy_path = config["taxonomy_path"]
    client_id = config["spotify_client_id"]
    client_secret = config["spotify_client_secret"]

    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set")
    if not input_csv or not os.path.isfile(input_csv):
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")
    if not output_json or not output_csv:
        raise ValueError("OUTPUT_JSON and OUTPUT_CSV must be set")
    if not taxonomy_path or not os.path.isfile(taxonomy_path):
        raise FileNotFoundError(f"Taxonomy not found: {taxonomy_path}")

    taxonomy = load_taxonomy(taxonomy_path)
    rows = _load_input_csv(input_csv)
    existing = _load_existing_json(output_json)
    lookup = _build_lookup(existing)

    sp = create_spotify_client(client_id, client_secret)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    todo_keys = set()
    for r in rows:
        k = r.lookup_key()
        if k not in lookup:
            todo_keys.add(k)

    # Fetch and tag only for (song, artist) not in lookup
    for (song_norm, artist_norm) in todo_keys:
        # Get one row to get song/artist display strings
        song_display = artist_display = ""
        for r in rows:
            if r.lookup_key() == (song_norm, artist_norm):
                song_display, artist_display = r.song, r.artist
                break
        match_result = match_track(sp, song_display, artist_display)
        if match_result["spotify_present"]:
            genres, tags, tag_source = tag_track(
                sp,
                match_result["spotify_track_id"],
                match_result["artist_id"],
                taxonomy,
            )
        else:
            genres, tags, tag_source = [], [], ""
        lookup[(song_norm, artist_norm)] = {
            "spotify_present": match_result["spotify_present"],
            "spotify_track_id": match_result["spotify_track_id"],
            "spotify_uri": match_result["spotify_uri"],
            "match_confidence": match_result["match_confidence"],
            "album_id": match_result["album_id"],
            "album_name": match_result["album_name"],
            "album_release_date": match_result["album_release_date"],
            "release_year": match_result["release_year"],
            "artist_id": match_result["artist_id"],
            "duration_ms": match_result["duration_ms"],
            "genres": genres,
            "tags": tags,
            "tag_source": tag_source,
        }

    # Build full list of EnrichedRecord (one per input row)
    records: list[EnrichedRecord] = []
    for r in rows:
        k = r.lookup_key()
        en = lookup.get(k) or {}
        rec = EnrichedRecord(
            season=r.season,
            episode_code=r.episode_code,
            episode_title=r.episode_title,
            overall_episode=r.overall_episode,
            song=r.song,
            artist=r.artist,
            note=r.note,
            source_url=r.source_url,
            source_api_url=r.source_api_url,
            spotify_present=en.get("spotify_present", False),
            spotify_track_id=en.get("spotify_track_id", ""),
            spotify_uri=en.get("spotify_uri", ""),
            match_confidence=float(en.get("match_confidence") or 0),
            album_id=en.get("album_id", ""),
            album_name=en.get("album_name", ""),
            album_release_date=en.get("album_release_date", ""),
            release_year=en.get("release_year", ""),
            artist_id=en.get("artist_id", ""),
            duration_ms=int(en.get("duration_ms") or 0),
            genres=list(en.get("genres") or []),
            tags=list(en.get("tags") or []),
            tag_source=en.get("tag_source", ""),
            last_updated=now_iso,
        )
        records.append(rec)

    # Write JSON to temp then replace
    out_dir = str(Path(output_json).parent)
    tmp_json = os.path.join(out_dir, Path(output_json).name + ".tmp")
    with open(tmp_json, "w") as f:
        json.dump([_record_to_dict(rec) for rec in records], f, indent=2)
    os.replace(tmp_json, output_json)

    # Derive CSV (scalar only) to temp then replace
    tmp_csv = os.path.join(out_dir, Path(output_csv).name + ".tmp")
    csv_columns = (
        list(records[0].to_csv_row().keys())
        if records
        else [
            "season", "episode_code", "episode_title", "overall_episode", "song", "artist",
            "note", "source_url", "source_api_url",
            "spotify_present", "spotify_track_id", "spotify_uri", "match_confidence",
            "album_id", "album_name", "album_release_date", "release_year", "artist_id",
            "duration_ms", "last_updated",
        ]
    )
    with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec.to_csv_row())
    os.replace(tmp_csv, output_csv)
    return (output_json, output_csv)


def main() -> None:
    """CLI entry point for the enrich script."""
    out_json, out_csv = run_enrichment()
    print(f"Enrichment done. JSON: {out_json}, CSV: {out_csv}")
