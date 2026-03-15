"""CLI entry point: run with python -m supernatural_soundtrack_scraper or the scrape script."""

from __future__ import annotations

from supernatural_soundtrack_scraper.core import fetch_wikitext, parse_songs
from supernatural_soundtrack_scraper.utils import export_csv, export_xlsx, load_config


def main() -> None:
    config = load_config()
    wikitext = fetch_wikitext(config["api_url"], config["page_title"])
    songs = parse_songs(wikitext)
    export_csv(songs, config["output_csv"])
    export_xlsx(songs, config["output_xlsx"])
    print("Exported soundtrack dataset.")


if __name__ == "__main__":
    main()
