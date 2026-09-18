"""Normalization: competitions/leagues."""

from models import LeagueSummary, LeagueProfile, StandingRow, TopScorer, MatchSummary


def normalize_league_summary(data: dict, country_data: dict | None = None) -> LeagueSummary:
    """Normalize a league dict into a canonical LeagueSummary."""
    from providers.api_football.adapters import ApiFootballAdapters
    return ApiFootballAdapters.league_summary(data, country_data)
