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

## What It Does

- Calls the MediaWiki API
- Downloads the page wikitext
- Extracts song and artist entries grouped by season
- Outputs CSV and Excel tables

## Project Structure

| Path | Description |
|------|-------------|
| `supernatural_soundtrack_scraper/` | Package: `core` (model, fetch, parse), `utils` (config, export), `cli`, `__main__.py` |
| `tests/` | Tests: `test_core.py`, `test_utils.py` |
| `config/scraper.yaml` | Scraper config (API URL, page title, output paths) |
| `pyproject.toml` | Poetry project, dependencies, and `scrape` script entry point |
| `poetry.lock` | Locked dependency versions (commit this) |
| [docs/SCRAPER_IMPROVEMENTS_PLAN.md](docs/SCRAPER_IMPROVEMENTS_PLAN.md) | Types, config-driven paths, Pydantic I/O (completed) |
| `SPOTIFY_ENRICHMENT_PLAN.md` | Planned Spotify enrichment roadmap |

## Tests

```bash
poetry run pytest tests/
```

## Roadmap

**Current focus (do first):**

- [docs/SCRAPER_IMPROVEMENTS_PLAN.md](docs/SCRAPER_IMPROVEMENTS_PLAN.md) - Type annotations, config-driven architecture, Pydantic for structured I/O (completed)

**Then:**

- [SPOTIFY_ENRICHMENT_PLAN.md](SPOTIFY_ENRICHMENT_PLAN.md) - Presence matching, taxonomy tagging
- [PLAYLIST_GENERATION_PLAN.md](PLAYLIST_GENERATION_PLAN.md) - Playlists by genre, mood, and uber playlist

## Contributing

Contributions are welcome via issues and pull requests.

## License

MIT License. See [LICENSE](LICENSE) for details.
