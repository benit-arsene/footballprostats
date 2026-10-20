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

# Available provider names (registered at runtime if credentials exist)
AVAILABLE_PROVIDERS: list[str] = ["api_football", "football_data"]

# football-data.org is registered but NOT selected as primary for any entity type
# until its data quality and coverage are verified.  API-Football remains the
# effective provider for all entity types.  To enable football-data.org for a
# specific entity type, change the corresponding entry above, e.g.:
#   "standings": {"primary": "football_data", "fallback": "api_football"}
