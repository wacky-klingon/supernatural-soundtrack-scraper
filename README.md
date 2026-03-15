# Supernatural Soundtrack Scraper

Scrapes song data from the Supernatural Fandom wiki page via the MediaWiki API and exports season-by-season soundtrack tables as CSV and Excel.

**Source:** https://supernatural.fandom.com/wiki/Supernatural_Music

## Prerequisites

- Python 3.x

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python scrape_supernatural_music.py
```

**Outputs:**

- `supernatural_soundtrack.csv`
- `supernatural_soundtrack.xlsx`

## What It Does

- Calls the MediaWiki API
- Downloads the page wikitext
- Extracts song and artist entries grouped by season
- Outputs CSV and Excel tables

## Project Structure

| File | Description |
|------|-------------|
| `scrape_supernatural_music.py` | Main scraping script |
| `requirements.txt` | Python dependencies |
| `supernatural_complete_soundtrack.csv` | Reference dataset (included) |
| `SPOTIFY_ENRICHMENT_PLAN.md` | Planned Spotify enrichment roadmap |

## Roadmap

Planned Spotify enrichment (presence matching, taxonomy tagging) is documented in [SPOTIFY_ENRICHMENT_PLAN.md](SPOTIFY_ENRICHMENT_PLAN.md).

## Contributing

Contributions are welcome via issues and pull requests.

## License

MIT License. See [LICENSE](LICENSE) for details.
