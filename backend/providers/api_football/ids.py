"""External ID extraction for API-Football provider."""

from typing import Any


def extract_team_external_ids(api_team: dict) -> list[tuple[str, str]]:
    """Extract external IDs from API-Football team response."""
    results: list[tuple[str, str]] = []
    if api_team and "id" in api_team:
        results.append(("api_football", str(api_team["id"])))
    return results


def extract_player_external_ids(api_player: dict) -> list[tuple[str, str]]:
    """Extract external IDs from API-Football player response."""
    results: list[tuple[str, str]] = []
    player = api_player.get("player", {}) if isinstance(api_player, dict) else {}
    if player and "id" in player:
        results.append(("api_football", str(player["id"])))
    return results


def extract_match_external_ids(api_fixture: dict) -> list[tuple[str, str]]:
    """Extract external IDs from API-Football fixture response."""
    results: list[tuple[str, str]] = []
    fixture = api_fixture.get("fixture", {}) if isinstance(api_fixture, dict) else {}
    if fixture and "id" in fixture:
        results.append(("api_football", str(fixture["id"])))
    return results


def extract_league_external_ids(api_league: dict) -> list[tuple[str, str]]:
    """Extract external IDs from API-Football league response."""
    results: list[tuple[str, str]] = []
    league = api_league.get("league", {}) if isinstance(api_league, dict) else {}
    if league and "id" in league:
        results.append(("api_football", str(league["id"])))
    return results
