"""Config loading and export helpers."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import yaml

from supernatural_soundtrack_scraper.core import SongRow


def load_config() -> dict[str, str]:
    """Load scraper config from config/scraper.yaml with optional env overrides."""
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "scraper.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    config.setdefault("api_url", "")
    config.setdefault("page_title", "")
    config.setdefault("output_csv", "")
    config.setdefault("output_xlsx", "")
    config["api_url"] = os.getenv("WIKI_API_URL", config["api_url"])
    config["page_title"] = os.getenv("WIKI_PAGE_TITLE", config["page_title"])
    config["output_csv"] = os.getenv("OUTPUT_CSV", config["output_csv"])
    config["output_xlsx"] = os.getenv("OUTPUT_XLSX", config["output_xlsx"])
    for key in ("output_csv", "output_xlsx"):
        p = config[key]
        if p and not Path(p).is_absolute():
            config[key] = str(project_root / p)
    return config


def export_csv(rows: list[SongRow], path: str) -> None:
    """Write song rows to a CSV file."""
    df = pd.DataFrame([r.model_dump() for r in rows])
    df.to_csv(path, index=False)


def export_xlsx(rows: list[SongRow], path: str) -> None:
    """Write song rows to an Excel file."""
    df = pd.DataFrame([r.model_dump() for r in rows])
    df.to_excel(path, index=False)
