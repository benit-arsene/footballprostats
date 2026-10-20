"""API-Football client service (provider wrapper).

Delegates to the provider layer for all external API calls.
Keeps backward-compatible function signatures so existing
routes continue to work unchanged.
"""

from providers.api_football.client import ApiFootballProvider, APIError, APIRateLimitError, APITimeoutError, APIConnectionError, APIInvalidResponseError
from providers.factory import build_provider_registry
from providers.routing import route_provider

_registry = build_provider_registry()
_api_football = ApiFootballProvider()


def _season_label(season: int | None) -> str | None:
    if season is None:
        return None
    try:
        y = int(season)
    except (TypeError, ValueError):
        return None
    return f"{y}/{y + 1}"


def _provider_for(entity_type: str, season: int | None = None, data_type: str | None = None):
    label = _season_label(season)
    name = route_provider(entity_type, season_label=label, data_type=data_type,
                          available_providers=set(_registry.list_providers()))
    try:
        return _registry.get_provider(name)
    except ValueError:
        return _api_football


async def get_fixture(fixture_id: int) -> dict | None:
    return await _api_football.get_fixture(fixture_id)


async def get_live_fixtures(league_id: int | None = None) -> list[dict]:
    return await _api_football.get_fixtures(league_id=league_id)


async def get_fixtures_by_date(date: str, league_id: int | None = None) -> list[dict]:
    return await _api_football.get_fixtures(date=date, league_id=league_id)


async def get_fixtures_by_team(team_id: int, season: int, league_id: int | None = None) -> list[dict]:
    p = _provider_for("match", season=season, data_type="fixtures")
    return await p.get_fixtures(team_id=team_id, season=season, league_id=league_id)


async def get_team(team_id: int) -> dict | None:
    return await _api_football.get_team(team_id)


async def get_team_players(team_id: int, season: int) -> list[dict]:
    return await _api_football.get_team_players(team_id, season)


async def search_team(name: str) -> list[dict]:
    return await _api_football.search_team(name)


async def get_player(player_id: int, season: int) -> dict | None:
    return await _api_football.get_player(player_id, season)


async def get_player_trophies(player_id: int) -> list[dict]:
    data = await _api_football.get_player(player_id, 0)
    return []


async def get_league(league_id: int, season: int) -> dict | None:
    return await _api_football.get_competition(league_id)


async def get_standings(league_id: int, season: int) -> list[dict]:
    p = _provider_for("standings", season=season, data_type="standings")
    return await p.get_standings(league_id, season)


async def get_top_scorers(league_id: int, season: int) -> list[dict]:
    return await _api_football.get_top_scorers(league_id, season)


__all__ = [
    "get_fixture", "get_live_fixtures", "get_fixtures_by_date",
    "get_fixtures_by_team", "get_team", "get_team_players",
    "search_team", "get_player", "get_player_trophies",
    "get_league", "get_standings", "get_top_scorers",
    "APIError", "APIRateLimitError", "APITimeoutError",
    "APIConnectionError", "APIInvalidResponseError",
]
