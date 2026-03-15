# Spotify Enrichment Plan

A multi-step feature guide for enriching the Supernatural soundtrack dataset with Spotify catalog presence and mood/context taxonomy tags.

---

## Overview

| Step | Goal | Output |
|------|------|--------|
| 1 | Define or adopt a taxonomy | `taxonomy.yaml` |
| 2 | Query Spotify, classify presence | `spotify_present` column |
| 3 | Tag found songs with taxonomy | `tags` column |

---

## Step 1: Taxonomy

### Option A: Borrow

**Spotify Genre Seeds** (from Spotify API / documentation):

- Use `available-genre-seeds` endpoint as a base
- Subset to relevant genres: `rock`, `classic-rock`, `hard-rock`, `metal`, `blues`, `country`, `southern-rock`, `alternative`, `punk`

**Mood/Context from Music Psychology**:

- Valence-arousal model: high/low valence, high/low arousal
- Common mood tags: `energetic`, `calm`, `sad`, `happy`, `aggressive`, `relaxed`

### Option B: Enhance (Recommended)

Combine borrowed tags with Supernatural-specific context tags:

```yaml
# taxonomy.yaml (conceptual)
genres:
  - rock
  - classic_rock
  - metal
  - blues
  - country
  - southern_rock
  - alternative

moods:
  - party        # high energy, danceable
  - sad          # low valence, melancholic
  - driving      # road-trip, highway
  - sipping_whiskey  # slow, reflective, bar vibe
  - brooding     # dark, intense
  - triumphant   # anthemic, climactic
```

**Mapping rules** (for Step 3):

- `genres`: from Spotify `artist.genres` (exact or substring match)
- `moods`: from Spotify Audio Features (energy, valence, danceability, tempo, acousticness) via thresholds defined in config

### Deliverable

- `config/taxonomy.yaml` with tag definitions and optional rule thresholds
- Document source (Spotify seeds, custom) and any extensions

---

## Step 2: Query Spotify, Classify Present / Not Present

### Input

- CSV: `season`, `episode_code`, `song`, `artist`, `note`, ...

### Process

1. Deduplicate by `(song, artist)` for efficiency
2. For each unique pair:
   - Search Spotify: `track:"{song}" artist:{artist}`
   - If results: take best match (exact artist match preferred)
   - Set `spotify_present`: `true` or `false`
   - If present: store `spotify_track_id`, `spotify_uri` for downstream use

### Matching Logic

| Scenario | Classification |
|----------|----------------|
| Exact match (song + artist) | `present` |
| Fuzzy match (typo, alternate spelling) | `present` (with confidence score) |
| No results | `not_present` |
| Ambiguous (multiple artists) | `present` if best match above threshold |

### Output Schema Addition

```
spotify_present, spotify_track_id, spotify_uri, match_confidence
```

### Deliverable

- Enriched CSV with presence flags
- `spotify_match_report.csv`: matched vs unmatched summary for manual review

---

## Step 3: Tag Taxonomy to Found Songs

### Input

- Enriched CSV from Step 2 (only rows where `spotify_present = true`)
- `taxonomy.yaml` from Step 1

### Process

1. For each matched track, fetch:
   - **Artist genres**: `GET /artists/{id}` -> `genres`
   - **Audio features**: `GET /audio-features/{id}` -> energy, valence, danceability, tempo, acousticness

2. Apply taxonomy rules:

   | Tag | Rule (example) |
   |-----|----------------|
   | rock | `"rock" in any artist.genres` |
   | party | `energy > 0.7 AND danceability > 0.5` |
   | sad | `valence < 0.3` |
   | driving | `energy > 0.6 AND tempo > 110` |
   | sipping_whiskey | `energy < 0.4 AND acousticness > 0.3` |

3. Store tags as multi-value: `tags` = `"rock,driving"` or JSON array

### Output Schema Addition

```
tags, tag_source
```

- `tags`: comma-separated or JSON
- `tag_source`: `spotify_genres` | `spotify_audio_features` | `hybrid`

### Deliverable

- Final CSV with `spotify_present`, `spotify_track_id`, `spotify_uri`, `tags`, `tag_source`
- Songs without Spotify match remain in dataset with `spotify_present=false`, `tags` empty

---

## Implementation Order

1. Create `config/taxonomy.yaml` (Step 1)
2. Implement `spotify_presence_matcher.py` (Step 2)
3. Implement `spotify_taxonomy_tagger.py` (Step 3)
4. Orchestrate via `supernatural_spotify_enricher.py` or CLI
5. Implement playlist generation (see [PLAYLIST_GENERATION_PLAN.md](PLAYLIST_GENERATION_PLAN.md))

---

## Spotify API Authentication

**Client Credentials (no user login, no scopes)** is sufficient for all enrichment steps.

| Step | Endpoint | Auth | Scopes |
|------|----------|------|--------|
| Search for tracks | `GET /search?q=track:...&type=track` | Client Credentials | None |
| Get track/artist | `GET /tracks/{id}`, `GET /artists/{id}` | Client Credentials | None |
| Get audio features | `GET /audio-features/{id}` | Client Credentials | None |

- **Credentials:** Client ID + Client Secret from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- **Flow:** `POST` to `https://accounts.spotify.com/api/token` with `grant_type=client_credentials`
- **Token:** Access token valid for ~1 hour

User OAuth and scopes (e.g. `playlist-modify-public`) are only needed if creating playlists in a user's account. For search, presence matching, and taxonomy tagging, Client Credentials alone is enough.

---

## Dependencies

- `spotipy` (Spotify Web API client)
- Spotify Developer account (Client ID, Client Secret)
- Client Credentials flow for enrichment (no user login, no scopes)

---

## Config-Driven Paths

All paths and taxonomy definitions in `config/` or `.env`:

- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
- `INPUT_CSV`, `OUTPUT_CSV`
- `TAXONOMY_PATH` -> `config/taxonomy.yaml`
