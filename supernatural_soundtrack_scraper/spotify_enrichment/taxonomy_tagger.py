"""Step 3: Tag matched tracks with taxonomy (genres + mood rules from audio features)."""

from __future__ import annotations

from typing import Any

from spotipy import Spotify


def tag_track(
    sp: Spotify,
    track_id: str,
    artist_id: str,
    taxonomy: dict[str, Any],
) -> tuple[list[str], list[str], str]:
    """
    Fetch artist genres and track audio features; apply taxonomy rules.
    Returns (genres_list, tags_list, tag_source).
    """
    genres: list[str] = []
    tags: list[str] = []
    tag_source = ""

    taxonomy_genres = (taxonomy.get("genres") or []) if isinstance(taxonomy.get("genres"), list) else []
    taxonomy_moods = (taxonomy.get("moods") or []) if isinstance(taxonomy.get("moods"), list) else []
    mood_rules = taxonomy.get("mood_rules") or {}

    # Fetch artist genres
    artist_genres: list[str] = []
    if artist_id:
        try:
            artist = sp.artist(artist_id)
            artist_genres = list(artist.get("genres") or [])
        except Exception:
            pass

    genres = list(artist_genres)
    genre_tags: list[str] = []
    for g in taxonomy_genres:
        g_norm = g.replace("_", " ").lower()
        for ag in artist_genres:
            if g_norm in ag.replace("-", " ").lower() or ag.replace("-", " ").lower() in g_norm:
                genre_tags.append(g)
                break

    # Fetch audio features for mood rules
    features: dict[str, Any] = {}
    if track_id:
        try:
            features = sp.audio_features([track_id])
            if features and features[0]:
                features = features[0]
            else:
                features = {}
        except Exception:
            features = {}

    mood_tags: list[str] = []
    if features and mood_rules:
        energy = float(features.get("energy") or 0)
        valence = float(features.get("valence") or 0)
        danceability = float(features.get("danceability") or 0)
        tempo = float(features.get("tempo") or 0)
        acousticness = float(features.get("acousticness") or 0)

        for mood, rules in mood_rules.items():
            if mood not in taxonomy_moods:
                continue
            if not isinstance(rules, dict):
                continue
            ok = True
            if "energy_min" in rules and energy < float(rules["energy_min"]):
                ok = False
            if "energy_max" in rules and energy > float(rules["energy_max"]):
                ok = False
            if "valence_min" in rules and valence < float(rules["valence_min"]):
                ok = False
            if "valence_max" in rules and valence > float(rules["valence_max"]):
                ok = False
            if "danceability_min" in rules and danceability < float(rules["danceability_min"]):
                ok = False
            if "tempo_min" in rules and tempo < float(rules["tempo_min"]):
                ok = False
            if "acousticness_min" in rules and acousticness < float(rules["acousticness_min"]):
                ok = False
            if ok:
                mood_tags.append(mood)

    tags = list(dict.fromkeys(genre_tags + mood_tags))
    if genre_tags and mood_tags:
        tag_source = "hybrid"
    elif genre_tags:
        tag_source = "spotify_genres"
    elif mood_tags:
        tag_source = "spotify_audio_features"
    return (genres, tags, tag_source)
