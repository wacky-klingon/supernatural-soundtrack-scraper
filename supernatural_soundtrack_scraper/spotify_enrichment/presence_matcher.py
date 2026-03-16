"""Step 2: Query Spotify, classify presence, persist track/album/artist."""

from __future__ import annotations

from typing import Any

from spotipy import Spotify
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials


def create_spotify_client(client_id: str, client_secret: str) -> Spotify:
    """Create a Spotipy client using client credentials (no user auth)."""
    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return Spotify(auth_manager=auth)


def match_track(sp: Spotify, song: str, artist: str) -> dict[str, Any]:
    """
    Search Spotify for track + artist. Return enrichment dict for Step 2 fields.
    Keys: spotify_present, spotify_track_id, spotify_uri, match_confidence,
    album_id, album_name, album_release_date, release_year, artist_id, duration_ms.
    """
    result: dict[str, Any] = {
        "spotify_present": False,
        "spotify_track_id": "",
        "spotify_uri": "",
        "match_confidence": 0.0,
        "album_id": "",
        "album_name": "",
        "album_release_date": "",
        "release_year": "",
        "artist_id": "",
        "duration_ms": 0,
    }
    if not song or not artist:
        return result

    query = f'track:"{song}" artist:{artist}'
    try:
        resp = sp.search(q=query, type="track", limit=5)
    except SpotifyException as exc:
        msg = (exc.msg or "").lower()
        # For the premium-subscription 403 case, stop the enrichment run.
        if exc.http_status == 403 and "active premium subscription required" in msg:
            raise RuntimeError(
                "Spotify enrichment requires an active premium subscription for this app. "
                "The Spotify API returned 403: active premium subscription required."
            ) from exc
        # For other 4xx/5xx errors, log and treat as not present.
        if 400 <= (exc.http_status or 0) < 600:
            print(f"Spotify API error ({exc.http_status}): {exc.msg}")
        return result
    except Exception as exc:
        # Unknown error: log and treat as not present.
        print(f"Unexpected error when calling Spotify search: {exc}")
        return result

    items = (resp.get("tracks") or {}).get("items") or []
    if not items:
        return result

    # Prefer exact artist name match (case-insensitive)
    artist_lower = artist.strip().lower()
    best = items[0]
    best_artist_name = ""
    if best.get("artists"):
        best_artist_name = (best["artists"][0].get("name") or "").strip().lower()
    for item in items:
        artists = item.get("artists") or []
        if not artists:
            continue
        name = (artists[0].get("name") or "").strip().lower()
        if name == artist_lower:
            best = item
            best_artist_name = name
            break

    result["spotify_present"] = True
    result["spotify_track_id"] = best.get("id") or ""
    result["spotify_uri"] = best.get("uri") or ""
    result["match_confidence"] = 1.0 if (best_artist_name == artist_lower) else 0.8

    album = best.get("album") or {}
    result["album_id"] = album.get("id") or ""
    result["album_name"] = album.get("name") or ""
    result["album_release_date"] = album.get("release_date") or ""
    release_date = result["album_release_date"]
    result["release_year"] = release_date[:4] if len(release_date) >= 4 else ""

    artists = best.get("artists") or []
    if artists:
        result["artist_id"] = artists[0].get("id") or ""
    result["duration_ms"] = int(best.get("duration_ms") or 0)

    return result
