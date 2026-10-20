"""Provider routing policy — season-aware provider selection.

This module implements a small, independently tested routing policy.
It does NOT modify PROVIDER_SELECTION or the registry.  Integration
into services and ingestion scripts is a separate phase.
"""

from __future__ import annotations

import os
from typing import Optional

from config import get_season_year

# Data types that football-data.org can supply on the free tier.
# Kept intentionally narrow — only verified capabilities.
FOOTBALL_DATA_SUPPORTED: frozenset[str] = frozenset({"fixtures", "standings"})

DEFAULT_PROVIDER = "api_football"
FOOTBALL_DATA_PROVIDER = "football_data"


def current_season_label() -> str:
    """Return the current football season label, e.g. '2026/2027'."""
    year = get_season_year()
    return f"{year}/{year + 1}"


def is_current_season(season_label: str | None) -> bool:
    """Return True if *season_label* matches the current football season."""
    if not season_label or not isinstance(season_label, str):
        return False
    parts = season_label.split("/")
    if len(parts) != 2:
        return False
    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError:
        return False
    return season_label == current_season_label() and end == start + 1


def is_football_data_available(available_providers: set[str] | None = None) -> bool:
    """Return True if football-data.org is registered/available."""
    if available_providers is not None:
        return FOOTBALL_DATA_PROVIDER in available_providers
    # Fall back to env-var check
    return bool(os.getenv("FOOTBALLDATA_KEY"))


def route_provider(
    entity_type: str,
    season_label: str | None = None,
    data_type: str | None = None,
    available_providers: set[str] | None = None,
) -> str:
    """Return the name of the provider to use for a given request.

    Rules:
    - API-Football is the safe default.
    - football-data.org is selected only when:
        1. It is registered/available.
        2. The season is the current season (or not specified, assumed current).
        3. The data type is in FOOTBALL_DATA_SUPPORTED.
    - Historical seasons, missing/malformed labels, and unsupported data
      types all route to API-Football.
    """
    resolved_type = data_type if data_type is not None else entity_type

    # Unsupported data type → API-Football
    if resolved_type not in FOOTBALL_DATA_SUPPORTED:
        return DEFAULT_PROVIDER

    # Missing or malformed season label → API-Football (safe default)
    if season_label is None or not is_current_season(season_label):
        return DEFAULT_PROVIDER

    # football-data.org not available → API-Football
    if not is_football_data_available(available_providers):
        return DEFAULT_PROVIDER

    return FOOTBALL_DATA_PROVIDER