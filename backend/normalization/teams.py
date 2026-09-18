"""Normalization: teams."""

from models import TeamSummary, TeamProfile, PlayerSummary, LeagueSummary


def normalize_team_summary(data: dict) -> TeamSummary:
    """Normalize a team dict into a canonical TeamSummary."""
    from providers.api_football.adapters import ApiFootballAdapters
    return ApiFootballAdapters.team_summary(data)


def normalize_team_profile(team_info: dict, players: list[PlayerSummary], league: LeagueSummary) -> TeamProfile:
    """Normalize team profile data into a canonical TeamProfile."""
    return TeamProfile(
        id=team_info["id"],
        name=team_info.get("name", ""),
        slug=team_info.get("slug", ""),
        short_name=team_info.get("short_name", "")[:3].upper() if team_info.get("short_name") else "",
        crest_url=team_info.get("logo", "") or team_info.get("crest_url", ""),
        league=league,
        founded=team_info.get("founded", 0),
        venue=team_info.get("venue", {}).get("name", "") if isinstance(team_info.get("venue"), dict) else "",
        coach=team_info.get("coach", "") if isinstance(team_info.get("coach"), dict) else "",
        squad=players,
    )
