# Supernatural Soundtrack Scraper

Scrapes song data from the Supernatural Fandom wiki page via the MediaWiki API and exports season-by-season soundtrack tables as CSV and Excel.

**Source:** https://supernatural.fandom.com/wiki/Supernatural_Music

## Prerequisites

- [Poetry](https://python-poetry.org/) (e.g. `pip install poetry` or the [official installer](https://python-poetry.org/docs/#installation))

## Installation

```bash
poetry install
```

Creates a virtual environment and installs dependencies from `pyproject.toml` and `poetry.lock`.

## Configuration

Paths and API settings are controlled by `config/scraper.yaml`. Keys:

| Key | Description |
|-----|-------------|
| `api_url` | MediaWiki API endpoint |
| `page_title` | Wiki page title (e.g. `Supernatural_Music`) |
| `output_csv` | Path for CSV output |
| `output_xlsx` | Path for Excel output |

Optional environment variables override YAML when set: `WIKI_API_URL`, `WIKI_PAGE_TITLE`, `OUTPUT_CSV`, `OUTPUT_XLSX`. See `.env.example`.

## Usage

From the project root:

```bash
poetry run scrape
```

Or run as a module:

```bash
poetry run python -m supernatural_soundtrack_scraper
```

Or activate the shell first, then run:

```bash
poetry shell
scrape
# or: python -m supernatural_soundtrack_scraper
```

**Outputs:** CSV and Excel files at the paths set in `config/scraper.yaml` (default: `supernatural_soundtrack.csv`, `supernatural_soundtrack.xlsx`).

### Spotify enrichment

Requires a soundtrack CSV (e.g. `supernatural_complete_soundtrack.csv`). Set `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env` (see `.env.example`). Paths are in `config/enrichment.yaml` (override with `INPUT_CSV`, `OUTPUT_JSON`, `OUTPUT_CSV`, `TAXONOMY_PATH`).

```bash
poetry run enrich
```

Writes JSON (source of truth, with genres/tags arrays) and a derived CSV (scalar columns only). Idempotent: re-runs skip (song, artist) pairs already in the output. See [SPOTIFY_ENRICHMENT.md](SPOTIFY_ENRICHMENT.md).

## What It Does

- Calls the MediaWiki API
- Downloads the page wikitext
- Extracts song and artist entries grouped by season
- Outputs CSV and Excel tables

## Project Structure

| Path | Description |
|------|-------------|
| `supernatural_soundtrack_scraper/` | Package: `core`, `utils`, `cli`, `spotify_enrichment` (presence matcher, taxonomy tagger, enricher) |
| `tests/` | Tests: `test_core.py`, `test_utils.py` |
| `config/scraper.yaml` | Scraper config (API URL, page title, output paths) |
| `config/enrichment.yaml` | Enrichment paths (input CSV, output JSON/CSV, taxonomy) |
| `config/taxonomy.yaml` | Taxonomy: genres, moods, mood rules for tagging |
| `pyproject.toml` | Poetry project, scripts: `scrape`, `enrich` |
| `poetry.lock` | Locked dependency versions (commit this) |
| [docs/SCRAPER_IMPROVEMENTS_PLAN.md](docs/SCRAPER_IMPROVEMENTS_PLAN.md) | Types, config-driven paths, Pydantic I/O (completed) |
| `SPOTIFY_ENRICHMENT.md` | Spotify enrichment design, pipeline, and data model |

## Tests

```bash
poetry run pytest tests/
```

## Roadmap

**Current focus (do first):**

- [docs/SCRAPER_IMPROVEMENTS_PLAN.md](docs/SCRAPER_IMPROVEMENTS_PLAN.md) - Type annotations, config-driven architecture, Pydantic for structured I/O (completed)

**Then:**

- [SPOTIFY_ENRICHMENT.md](SPOTIFY_ENRICHMENT.md) - Presence matching, taxonomy tagging
- [PLAYLIST_GENERATION_PLAN.md](PLAYLIST_GENERATION_PLAN.md) - Playlists by genre, mood, and uber playlist

## Contributing

Contributions are welcome via issues and pull requests.

## License

MIT License. See [LICENSE](LICENSE) for details.
