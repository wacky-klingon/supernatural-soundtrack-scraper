"""Core scraping logic: model, API fetch, and wikitext parsing."""

from __future__ import annotations

import re

import requests
from pydantic import BaseModel


class SongRow(BaseModel):
    """One scraped song row: season, song title, artist."""

    season: int
    song: str
    artist: str


def fetch_wikitext(api_url: str, page_title: str) -> str:
    """Fetch raw wikitext for the given page from the MediaWiki API."""
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": page_title,
    }
    r = requests.get(api_url, params=params)
    r.raise_for_status()
    data = r.json()
    page = next(iter(data["query"]["pages"].values()))
    return page["revisions"][0]["slots"]["main"]["*"]


def parse_songs(text: str) -> list[SongRow]:
    """Parse wikitext into a list of SongRow by season."""
    rows: list[SongRow] = []
    current_season: int | None = None

    season_pattern = re.compile(r"=+\s*Season\s+(\d+)\s*=+", re.IGNORECASE)
    song_pattern = re.compile(r'\*\s*"([^"]+)"\s*[–-]\s*([^\n]+)')

    for line in text.splitlines():
        s = season_pattern.search(line)
        if s:
            current_season = int(s.group(1))
            continue

        m = song_pattern.search(line)
        if m and current_season is not None:
            song = m.group(1).strip()
            artist = m.group(2).strip()
            rows.append(
                SongRow(season=current_season, song=song, artist=artist)
            )

    return rows
