"""Provider selection configuration.

Maps entity types to primary/fallback providers.
Each entity type (competition, season, team, player, match, standings, etc.)
can have a primary provider and an optional fallback provider.

Example:
    PROVIDER_SELECTION = {
        "team": {"primary": "api_football"},
        "match": {"primary": "api_football", "fallback": "provider_b"},
        "standings": {"primary": "api_football"},
    }
"""

PROVIDER_SELECTION: dict[str, dict[str, str]] = {
    "competition": {"primary": "api_football"},
    "season": {"primary": "api_football"},
    "team": {"primary": "api_football"},
    "player": {"primary": "api_football"},
    "match": {"primary": "api_football"},
    "standings": {"primary": "api_football"},
    "top_scorers": {"primary": "api_football"},
}
