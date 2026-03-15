# Scraper Improvements Plan (Priority)

Addresses code-quality and architecture gaps in the main scraper so it aligns with project rules before extending with Spotify enrichment and playlist generation.

---

## Overview

| Priority | Gap | Goal |
|----------|-----|------|
| 1 | Type annotations | All public functions and class methods use explicit type annotations |
| 2 | Config-driven architecture | API URL, page name, and output paths come from config or .env |
| 3 | Pydantic for structured I/O | Use pydantic models for scraped rows and export schema instead of raw dicts/DataFrame |

---

## 1. Type Annotations

**Rule:** All public functions and class methods must use explicit type annotations.

**Current state:** `fetch_wikitext()`, `parse_songs(text)`, and `main()` have no parameter or return types.

**Changes:**

1. Add return type to `fetch_wikitext()`: `-> str`.
2. Add parameter and return types to `parse_songs(text: str) -> list[dict[str, Any]]` or, preferably, `-> list[SongRow]` once a Pydantic model exists (see Section 3).
3. Add return type to `main()`: `-> None`.
4. Use `from __future__ import annotations` at top of file if targeting Python 3.9 and using `list[SongRow]` (or use `List[SongRow]` from `typing` for 3.8).

**Deliverable:** No public function or method in `scrape_supernatural_music.py` without full type annotations.

---

## 2. Config-Driven Architecture

**Rule:** All data paths, model params, and output targets must be controlled via YAML or .env files. Never hardcode absolute paths or API credentials.

**Current state:** `API_URL`, `PAGE`, and output file paths are hardcoded in `scrape_supernatural_music.py`.

**Changes:**

1. **Config file:** Create `config/scraper.yaml` (or equivalent) with:
   - `api_url`: MediaWiki API endpoint
   - `page_title`: Wiki page title (e.g. `Supernatural_Music`)
   - `output_csv`: path for CSV output (e.g. `supernatural_soundtrack.csv` or under an output dir)
   - `output_xlsx`: path for Excel output

2. **Alternative or supplement:** Add to `.env.example` and support env vars such as:
   - `WIKI_API_URL`
   - `WIKI_PAGE_TITLE`
   - `OUTPUT_CSV`
   - `OUTPUT_XLSX`

3. **Loading:** In the script, load config at startup (e.g. PyYAML for YAML, `os.getenv` with defaults for .env). Prefer a single source of truth (e.g. YAML with optional env overrides).

4. **Paths:** Use paths relative to project root or explicit config; no hardcoded literals for API URL, page name, or output paths inside the script.

**Deliverable:** `config/scraper.yaml` (and/or .env) drives all URLs and paths; script reads them and documents expected keys in this plan or README.

---

## 3. Pydantic for Structured I/O

**Rule:** Use pydantic.BaseModel for structured data inputs and outputs, especially in API-facing or CLI-exposed modules.

**Current state:** Script uses plain dicts for rows and pandas DataFrame for export; no validated schema.

**Changes:**

1. **Model for a single row:** Define a `SongRow` (or `ScrapedSong`) pydantic model with fields:
   - `season: int`
   - `song: str`
   - `artist: str`

2. **Parsing:** Have `parse_songs(text: str) -> list[SongRow]` (or `list[ScrapedSong]`) build and return a list of validated models instead of dicts.

3. **Export:** For CSV/Excel export, convert `list[SongRow]` to DataFrame (or serialize via model_dump) before writing. Keep export logic separate (one function for writing CSV, one for Excel, or one that takes format from config).

4. **Dependency:** Add `pydantic` (and optionally `pydantic-settings` if using it for config) to `requirements.txt`.

**Deliverable:** Scraper output is defined by a pydantic model; parsing produces a list of model instances; export consumes that list. No raw dicts for the core song row schema.

---

## Implementation Order

1. Add pydantic to requirements and define `SongRow` (or `ScrapedSong`) model.
2. Add type annotations to all public functions, using the new model in `parse_songs` return type.
3. Introduce `config/scraper.yaml` (and/or .env) and load API URL, page title, and output paths in the script.
4. Refactor `parse_songs` to return `list[SongRow]`; refactor export to accept `list[SongRow]`.
5. Update README to document config keys and optional .env overrides.

---

## Dependencies

- `pydantic` (and optionally `pydantic-settings` for config)
- `pyyaml` if using `config/scraper.yaml`

---

## Links

- [README](README.md) - Project overview and roadmap
- [SPOTIFY_ENRICHMENT_PLAN.md](SPOTIFY_ENRICHMENT_PLAN.md) - Enrichment (after scraper improvements)
- [PLAYLIST_GENERATION_PLAN.md](PLAYLIST_GENERATION_PLAN.md) - Playlist generation (after enrichment)
