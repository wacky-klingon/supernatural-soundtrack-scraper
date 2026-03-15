"""Tests for config and export utils."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from supernatural_soundtrack_scraper.core import SongRow
from supernatural_soundtrack_scraper.utils import export_csv, export_xlsx, load_config


def test_load_config_returns_expected_keys() -> None:
    config = load_config()
    assert "api_url" in config
    assert "page_title" in config
    assert "output_csv" in config
    assert "output_xlsx" in config
    assert config["page_title"] == "Supernatural_Music"


def test_export_csv_writes_expected_content() -> None:
    rows = [SongRow(season=1, song="Test Song", artist="Test Artist")]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.csv"
        export_csv(rows, str(path))
        assert path.exists()
        content = path.read_text()
        assert "season" in content
        assert "Test Song" in content
        assert "Test Artist" in content


def test_export_xlsx_writes_file() -> None:
    rows = [SongRow(season=1, song="Test Song", artist="Test Artist")]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.xlsx"
        export_xlsx(rows, str(path))
        assert path.exists()
        assert path.stat().st_size > 0
