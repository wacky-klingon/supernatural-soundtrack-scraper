# Spotify Enrichment Plan

A multi-step feature guide for enriching the Supernatural soundtrack dataset with Spotify catalog presence and mood/context taxonomy tags.

---

## Overview

| Step | Goal | Output |
|------|------|--------|
| 1 | Define or adopt a taxonomy | `taxonomy.yaml` |
| 2 | Query Spotify, classify presence + persist track/album/artist | `spotify_present`, track/album/year columns |
| 3 | Tag found songs with taxonomy | `tags` column |

The soundtrack list is static (show ended); no retry of not-found tracks.

---

## Data Model: JSON Source of Truth, CSV Derived View

Two outputs; both are one row (or one object) per (season, episode, song, artist) appearance. All paths are config-driven.

**Input:** e.g. `supernatural_complete_soundtrack.csv` — columns: `season`, `episode_code`, `episode_title`, `overall_episode`, `song`, `artist`, `note`, `source_url`, `source_api_url`.

**JSON (source of truth):** e.g. `Spotify_supernatural.json` — array of objects with full data. Each object has input columns plus:

| Field | Source | Notes |
|--------|--------|--------|
| `spotify_present` | Step 2 | `true` / `false` |
| `spotify_track_id` | Step 2 | Spotify track ID |
| `spotify_uri` | Step 2 | `spotify:track:...` |
| `match_confidence` | Step 2 | Optional score |
| `album_id` | Step 2 | Spotify album ID |
| `album_name` | Step 2 | From track.album.name |
| `album_release_date` | Step 2 | Raw from API (YYYY, YYYY-MM, or YYYY-MM-DD) |
| `release_year` | Step 2 | First 4 chars of album_release_date for filtering |
| `artist_id` | Step 2 | Primary artist ID (or first); multi-artist pipe-separated if needed |
| `duration_ms` | Step 2 | Track duration |
| `genres` | Step 3 | Array of strings from Spotify artist.genres (used for taxonomy) |
| `tags` | Step 3 | Array of taxonomy tag strings (from genre rules + audio-feature rules); dedupe when building |
| `tag_source` | Step 3 | `spotify_genres` \| `spotify_audio_features` \| `hybrid` |
| `last_updated` | Enricher | ISO timestamp when row was last enriched |

Songs without a Spotify match keep `spotify_present=false`, Spotify fields empty, `genres`/`tags` empty arrays; `last_updated` still set. Downstream consumers that need tags or genres use the JSON file.

**CSV (derived view):** e.g. `Spotify_supernatural.csv` — same rows, scalar columns only. Generated from the JSON after each run. Contains input columns plus: `spotify_present`, `spotify_track_id`, `spotify_uri`, `match_confidence`, `album_id`, `album_name`, `album_release_date`, `release_year`, `artist_id`, `duration_ms`, `last_updated`. No `genres`, `tags`, or `tag_source` (avoids CSV delimiter issues and keeps the file spreadsheet-safe).

---

## Idempotent Run and Resume

- **Feed:** Input CSV (e.g. `supernatural_complete_soundtrack.csv`) is the source of rows.
- **Output:** JSON is the source of truth; CSV is derived from it. Config: `INPUT_CSV`, `OUTPUT_JSON`, `OUTPUT_CSV`.
- **On startup:** If `OUTPUT_JSON` exists, load it and build a lookup keyed by normalized `(song, artist)` -> full enrichment object (including `genres`, `tags`). Any row with `spotify_present` set (true or false) is treated as already processed; do not re-query Spotify for that (song, artist).
- **Run:** From input, collect unique `(song, artist)`; subtract those already in the lookup. Call Spotify only for the remainder. For every input row, fill enrichment from lookup (already done) or from fresh API result; set `last_updated` to this run’s timestamp.
- **Write (JSON):** Write the full result (array of objects, including `genres` and `tags` arrays) to a temp file in the same directory as the output (e.g. `Spotify_supernatural.json.tmp`). When done, atomically replace: `os.replace(temp_path, output_path)`. This avoids partial/corrupt output on crash.
- **Write (CSV):** Derive CSV from the in-memory result (or re-read the new JSON): one row per object, scalar columns only (no `genres`, `tags`, `tag_source`). Write to a temp CSV in the same directory, then atomically replace the CSV file with `os.replace`. CSV is always generated from the same data as the JSON so the two stay in sync.

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
   - If present: store `spotify_track_id`, `spotify_uri`, and from the track object persist `album.id`, `album.name`, `album.release_date`, primary artist `id`, `duration_ms`; derive `release_year` from first 4 chars of `album.release_date` for filtering

### Matching Logic

| Scenario | Classification |
|----------|----------------|
| Exact match (song + artist) | `present` |
| Fuzzy match (typo, alternate spelling) | `present` (with confidence score) |
| No results | `not_present` |
| Ambiguous (multiple artists) | `present` if best match above threshold |

### Output Schema Addition (Step 2 columns)

Step 2 adds to the JSON object: `spotify_present`, `spotify_track_id`, `spotify_uri`, `match_confidence`, `album_id`, `album_name`, `album_release_date`, `release_year`, `artist_id`, `duration_ms`. The enricher sets `last_updated` when writing. See [Data Model: JSON Source of Truth, CSV Derived View](#data-model-json-source-of-truth-csv-derived-view).

### Deliverable

- Enriched JSON (and derived CSV) with presence flags and track/album/artist/year fields
- Optional: `spotify_match_report.csv` — matched vs unmatched summary for manual review

---

## Step 3: Tag Taxonomy to Found Songs

### Input

- Enriched data from Step 2 (only rows where `spotify_present = true`); in implementation this is the in-memory list or JSON
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

3. Store in JSON: `genres` as array of strings (from Spotify); `tags` as array of taxonomy tag strings (dedupe when building); `tag_source` as one of `spotify_genres` | `spotify_audio_features` | `hybrid`. CSV export omits these fields (see [Data Model](#data-model-json-source-of-truth-csv-derived-view)).

### Output Schema Addition

- **JSON:** `genres` (array), `tags` (array), `tag_source` (string)
- **CSV:** derived view has no `genres`, `tags`, or `tag_source` columns

### Deliverable

- Final JSON (source of truth) with all fields including `genres`, `tags`, `tag_source`, and `last_updated`; derived CSV with scalar columns only
- Songs without Spotify match remain in dataset with `spotify_present=false`, `genres`/`tags` empty arrays, Spotify fields blank; `last_updated` still set

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
- `INPUT_CSV` — source soundtrack (e.g. `supernatural_complete_soundtrack.csv`)
- `OUTPUT_JSON` — source of truth (e.g. `Spotify_supernatural.json`)
- `OUTPUT_CSV` — derived view, scalar columns only (e.g. `Spotify_supernatural.csv`); generated from JSON after each run
- `TAXONOMY_PATH` -> `config/taxonomy.yaml`
