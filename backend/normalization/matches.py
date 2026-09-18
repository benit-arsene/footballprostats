"""Normalization modules — validate, transform, and deduplicate provider data
into canonical models.

Each module handles one entity type. They receive raw provider responses
(or adapter output) and produce canonical model instances from models.py.

The key principle: no provider-specific fields leak into canonical models.
Normalization validates that multiple providers converge to the same shape.
"""

from models import (
    MatchSummary,
    MatchDetail,
    MatchStatus,
    EventType,
    TeamSummary,
    PlayerSummary,
    LeagueSummary,
    StandingRow,
    TopScorer,
)

__all__ = [
    "normalize_match_summary",
    "normalize_match_detail",
    "normalize_standing_row",
    "normalize_top_scorer",
]


def normalize_match_summary(data: dict) -> MatchSummary:
    """Normalize a fixture dict into a canonical MatchSummary.

    Accepts API-Football fixture format (as produced by adapters).
    Future: can accept other provider formats and converge to same output.
    """
    from providers.api_football.adapters import ApiFootballAdapters
    return ApiFootballAdapters.match_summary(data)


def normalize_match_detail(data: dict) -> MatchDetail:
    """Normalize a fixture dict into a canonical MatchDetail."""
    from providers.api_football.adapters import ApiFootballAdapters
    return ApiFootballAdapters.match_detail(data)


def normalize_standing_row(data: dict) -> StandingRow:
    """Normalize a standing row dict into a canonical StandingRow."""
    from providers.api_football.adapters import ApiFootballAdapters
    return ApiFootballAdapters.standing_row(data)


def normalize_top_scorer(data: dict) -> TopScorer:
    """Normalize a top scorer dict into a canonical TopScorer."""
    from providers.api_football.adapters import ApiFootballAdapters
    return ApiFootballAdapters.top_scorer(data)
