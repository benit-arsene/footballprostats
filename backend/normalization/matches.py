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


def _is_football_data_match(data: dict) -> bool:
    """True when the payload uses the football-data.org v4 match shape."""
    return "homeTeam" in data and "utcDate" in data


def normalize_match_summary(data: dict) -> MatchSummary:
    """Normalize a fixture dict into a canonical MatchSummary.

    Accepts API-Football fixture format (as produced by adapters) and the
    football-data.org v4 match format. Both converge to the same output.
    """
    if _is_football_data_match(data):
        from providers.football_data.adapters import FootballDataAdapters
        return FootballDataAdapters.match_summary(data)

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
