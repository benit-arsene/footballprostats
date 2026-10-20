"""External ID extraction for football-data.org provider."""

from typing import Any


def extract_team_external_ids(api_team: dict) -> list[tuple[str, str]]:
    """Extract external IDs from football-data.org team response."""
    results: list[tuple[str, str]] = []
    if api_team and "id" in api_team:
        results.append(("football_data", str(api_team["id"])))
    return results


def extract_player_external_ids(api_player: dict) -> list[tuple[str, str]]:
    """Extract external IDs from football-data.org player response."""
    results: list[tuple[str, str]] = []
    if api_player and "id" in api_player:
        results.append(("football_data", str(api_player["id"])))
    return results


def extract_match_external_ids(api_match: dict) -> list[tuple[str, str]]:
    """Extract external IDs from football-data.org match response."""
    results: list[tuple[str, str]] = []
    if api_match and "id" in api_match:
        results.append(("football_data", str(api_match["id"])))
    return results


def extract_competition_external_ids(api_comp: dict) -> list[tuple[str, str]]:
    """Extract external IDs from football-data.org competition response."""
    results: list[tuple[str, str]] = []
    if api_comp and "id" in api_comp:
        results.append(("football_data", str(api_comp["id"])))
    return results