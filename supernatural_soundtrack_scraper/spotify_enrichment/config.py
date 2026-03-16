"""Load enrichment and taxonomy config from YAML and env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_path(p: str, base: Path | None = None) -> str:
    if not p:
        return p
    base = base or _PROJECT_ROOT
    path = Path(p)
    if not path.is_absolute():
        path = base / p
    return str(path.resolve())


def load_enrichment_config() -> dict[str, Any]:
    """Load config from config/enrichment.yaml with env overrides. Resolve paths relative to project root."""
    config_path = _PROJECT_ROOT / "config" / "enrichment.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    config.setdefault("input_csv", "")
    config.setdefault("output_json", "")
    config.setdefault("output_csv", "")
    config.setdefault("taxonomy_path", "")
    config["input_csv"] = os.getenv("INPUT_CSV", config["input_csv"])
    config["output_json"] = os.getenv("OUTPUT_JSON", config["output_json"])
    config["output_csv"] = os.getenv("OUTPUT_CSV", config["output_csv"])
    config["taxonomy_path"] = os.getenv("TAXONOMY_PATH", config["taxonomy_path"])
    for key in ("input_csv", "output_json", "output_csv", "taxonomy_path"):
        if config[key]:
            config[key] = _resolve_path(config[key])
    config["spotify_client_id"] = os.getenv("SPOTIFY_CLIENT_ID", "")
    config["spotify_client_secret"] = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    return config


def load_taxonomy(taxonomy_path: str) -> dict[str, Any]:
    """Load taxonomy YAML (genres, moods, mood_rules)."""
    with open(taxonomy_path) as f:
        return yaml.safe_load(f) or {}
