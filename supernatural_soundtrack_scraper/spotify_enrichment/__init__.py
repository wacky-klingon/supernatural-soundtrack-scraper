"""Spotify enrichment: presence matching, taxonomy tagging, and orchestration."""

from supernatural_soundtrack_scraper.spotify_enrichment.enricher import run_enrichment
from supernatural_soundtrack_scraper.spotify_enrichment.models import EnrichedRecord

__all__ = ["run_enrichment", "EnrichedRecord"]
