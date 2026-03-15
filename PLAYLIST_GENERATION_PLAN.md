# Playlist Generation Plan

Extends the Spotify enrichment pipeline. After classification and taxonomy tagging (Steps 1-3 of SPOTIFY_ENRICHMENT_PLAN.md), generate playlists by genre, by mood, and one uber playlist.

---

## Prerequisites

- Enriched CSV from Spotify enrichment (Steps 1-3)
- Columns: `spotify_present`, `spotify_track_id`, `spotify_uri`, `tags`, `tag_source`
- Taxonomy in `config/taxonomy.yaml` with `genres` and `moods` sections

---

## Overview

| Step | Goal | Output |
|------|------|--------|
| 4a | Parse tags into genre vs mood | Internal grouping |
| 4b | Generate playlists per genre | `playlists/by_genre/<genre>.m3u` |
| 4c | Generate playlists per mood | `playlists/by_mood/<mood>.m3u` |
| 4d | Generate uber playlist | `playlists/supernatural_complete.m3u` |

---

## Tag Parsing

Tags from Step 3 are comma-separated (e.g. `"rock,driving,classic_rock"`). Parse against `taxonomy.yaml`:

- `genres`: rock, classic_rock, metal, blues, country, southern_rock, alternative
- `moods`: party, sad, driving, sipping_whiskey, brooding, triumphant

Each tag maps to exactly one category (genre or mood). Songs can have multiple tags in both categories.

---

## Playlist Output Formats

### Option A: M3U (Recommended)

Standard playlist format. Each line is a Spotify URI or extended format:

```
#EXTM3U
#EXTINF:-1,AC/DC - Back In Black
spotify:track:3z4htdZJQFJ3QcZmGL1YkP
#EXTINF:-1,Lynyrd Skynyrd - Free Bird
spotify:track:...
```

- Portable, no Spotify account needed to generate
- Users can import into Spotify, VLC, or other players
- Config-driven output path: `config/playlists_output_dir` or `playlists/`

### Option B: JSON Manifest

Machine-readable manifest for downstream tools:

```json
{
  "by_genre": {
    "rock": ["spotify:track:...", "spotify:track:..."],
    "metal": ["spotify:track:..."]
  },
  "by_mood": {
    "driving": ["spotify:track:..."],
    "sad": ["spotify:track:..."]
  },
  "uber": ["spotify:track:...", "spotify:track:..."]
}
```

### Option C: Push to Spotify (Optional)

Create playlists in a user's Spotify account via API. Requires:

- User OAuth flow (not Client Credentials)
- Scopes: `playlist-modify-public` or `playlist-modify-private`
- User runs auth once; script creates/updates playlists

---

## Step 4a: Parse Tags

**Input:** Enriched CSV, taxonomy.yaml

**Process:**

1. Load taxonomy genres and moods
2. For each row with `spotify_present=true` and non-empty `tags`:
   - Split tags by comma
   - Classify each tag as genre or mood via taxonomy lookup
   - Build sets: `genre_tags`, `mood_tags`

**Output:** In-memory or intermediate CSV with `genre_tags`, `mood_tags` columns (optional)

---

## Step 4b: Playlists per Genre

**Input:** Tagged rows (spotify_present=true)

**Process:**

1. For each genre in taxonomy:
   - Filter rows where genre in genre_tags
   - Deduplicate by spotify_track_id (first occurrence wins)
   - Sort by season, episode (optional) or artist
   - Write M3U: `playlists/by_genre/rock.m3u`, etc.

**Output:**

```
playlists/
  by_genre/
    rock.m3u
    classic_rock.m3u
    metal.m3u
    blues.m3u
    ...
```

---

## Step 4c: Playlists per Mood

**Input:** Tagged rows (spotify_present=true)

**Process:**

1. For each mood in taxonomy:
   - Filter rows where mood in mood_tags
   - Deduplicate by spotify_track_id
   - Sort by season, episode or artist
   - Write M3U: `playlists/by_mood/driving.m3u`, etc.

**Output:**

```
playlists/
  by_mood/
    driving.m3u
    sad.m3u
    sipping_whiskey.m3u
    brooding.m3u
    ...
```

---

## Step 4d: Uber Playlist

**Input:** All rows with spotify_present=true

**Process:**

1. Collect all unique spotify_uri (dedupe by track_id)
2. Sort by season, overall_episode, then artist (chronological order)
3. Write M3U: `playlists/supernatural_complete.m3u`

**Output:**

```
playlists/
  supernatural_complete.m3u
```

---

## Implementation

### New Script: `playlist_generator.py`

**Responsibilities:**

- Load enriched CSV
- Load taxonomy
- Parse tags into genre/mood
- Generate M3U files (and optionally JSON manifest)
- Idempotent: overwrite playlists on each run

**Config (config/ or .env):**

- `ENRICHED_CSV` - path to tagged CSV
- `TAXONOMY_PATH` - config/taxonomy.yaml
- `PLAYLISTS_OUTPUT_DIR` - playlists/ (default)

### Orchestration

Extend `supernatural_spotify_enricher.py` (or CLI) to optionally run playlist generation after Step 3:

```
scrape -> presence match -> taxonomy tag -> [playlist generate]
```

Or run standalone:

```
python playlist_generator.py --input supernatural_enriched.csv
```

---

## Edge Cases

| Case | Handling |
|------|----------|
| Song has no tags | Include in uber only, exclude from genre/mood playlists |
| Empty genre/mood | Skip writing that playlist file |
| Duplicate tracks | Dedupe by spotify_track_id, keep first occurrence |
| Taxonomy updated | Re-run generator; playlists are regenerated |

---

## Implementation Order

1. Implement `playlist_generator.py` (Steps 4a-4d)
2. Add `PLAYLISTS_OUTPUT_DIR` to config
3. Add `playlists/` to .gitignore (generated output) or commit sample playlists
4. Document in README

---

## Dependencies

- No new dependencies (pandas, standard library sufficient for M3U/JSON)
- Spotify API not required for playlist file generation (only for enrichment)
