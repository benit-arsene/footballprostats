"""
Mapper: API-Football JSON → our Pydantic models.

Delegates to the normalization layer for canonical model mapping.
Keeps backward-compatible function signatures for existing routes.
"""

from normalization.matches import (
    normalize_match_summary,
    normalize_match_detail,
    normalize_standing_row,
    normalize_top_scorer,
)
from normalization.teams import normalize_team_summary
from normalization.players import normalize_player_summary
from models import (
    MatchSummary,
    MatchDetail,
    MatchStatus,
    EventType,
    TeamSummary,
    PlayerSummary,
    LeagueSummary,
    MatchEvent,
    MatchStats,
    LineupPlayer,
    StandingRow,
    TopScorer,
    TeamProfile,
    PlayerProfile,
    CareerStats,
    MatchLogEntry,
)


def _status_map(api_status: str, elapsed: int | None) -> MatchStatus:
    mapping = {
        "NS": "scheduled", "TBD": "scheduled",
        "1H": "live", "HT": "live", "2H": "live",
        "ET": "live", "P": "live", "BT": "live", "LIVE": "live",
        "FT": "finished", "PST": "postponed", "CANC": "cancelled",
        "AWD": "finished", "WO": "finished",
    }
    return mapping.get(api_status, "scheduled")


def _event_type_map(api_type: str, api_detail: str | None) -> EventType:
    from normalization.events import normalize_event_type
    return normalize_event_type(api_type, api_detail)


def _league_id_to_name(league_id: int) -> tuple[str, str]:
    names = {
        39: ("Premier League", "England"),
        140: ("La Liga", "Spain"),
        2: ("Champions League", "Europe"),
        78: ("Bundesliga", "Germany"),
        135: ("Serie A", "Italy"),
        61: ("Ligue 1", "France"),
    }
    name, country = names.get(league_id, ("Unknown League", "Unknown"))
    return name, country


def _make_slug(name: str, id: int) -> str:
    import re
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return f"{slug}-{id}"


make_slug = _make_slug


def map_team_summary(api_team: dict) -> TeamSummary:
    return normalize_team_summary(api_team)


def map_league_summary(api_league: dict, api_country: dict | None = None) -> LeagueSummary:
    from normalization.competitions import normalize_league_summary
    return normalize_league_summary(api_league, api_country)


def map_player_summary(api_player: dict) -> PlayerSummary:
    return normalize_player_summary(api_player)


def map_match_summary(fixture: dict) -> MatchSummary:
    return normalize_match_summary(fixture)


def map_match_detail(fixture: dict) -> MatchDetail:
    return normalize_match_detail(fixture)


def map_standing_row(api_row: dict) -> StandingRow:
    return normalize_standing_row(api_row)


def map_top_scorer(api_player: dict) -> TopScorer:
    return normalize_top_scorer(api_player)
