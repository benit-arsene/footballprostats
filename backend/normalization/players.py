"""Normalization: players."""

from models import PlayerSummary, PlayerProfile, CareerStats, MatchLogEntry, TeamSummary


def normalize_player_summary(data: dict) -> PlayerSummary:
    """Normalize a player dict into a canonical PlayerSummary."""
    from providers.api_football.adapters import ApiFootballAdapters
    return ApiFootballAdapters.player_summary(data)


def normalize_player_profile(
    player_info: dict,
    current_team: TeamSummary,
    career: CareerStats,
    match_logs: list[MatchLogEntry],
) -> PlayerProfile:
    """Normalize player profile data into a canonical PlayerProfile."""
    return PlayerProfile(
        id=player_info["id"],
        name=player_info.get("name", ""),
        slug=player_info.get("slug", ""),
        position=player_info.get("position", ""),
        number=player_info.get("number"),
        nationality=player_info.get("nationality", ""),
        date_of_birth=player_info.get("date_of_birth", " "),
        height_cm=player_info.get("height_cm"),
        foot=player_info.get("foot", ""),
        team=current_team,
        career_stats=career,
        match_logs=match_logs,
    )
