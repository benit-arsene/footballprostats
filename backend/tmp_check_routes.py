"""Route compatibility check."""
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

try:
    import main
    print("OK: main")
except Exception as e:
    print(f"FAIL: main: {e}")
    sys.exit(1)

try:
    from routes import matches, teams, players, leagues
    print("OK: routes")
except Exception as e:
    print(f"FAIL: routes: {e}")
    sys.exit(1)

try:
    from services import football_api
    print("OK: services.football_api")
except Exception as e:
    print(f"FAIL: services.football_api: {e}")
    sys.exit(1)

try:
    from services import mapper
    print("OK: services.mapper")
except Exception as e:
    print(f"FAIL: services.mapper: {e}")
    sys.exit(1)

# Check route functions exist
import inspect
from routes.matches import get_live_matches, get_live_matches_summary, get_matches_by_date, get_match_detail, get_match_events
from routes.teams import get_team_profile
from routes.players import get_player_profile
from routes.leagues import get_league_profile

for fn in [get_live_matches, get_live_matches_summary, get_matches_by_date, get_match_detail, get_match_events,
           get_team_profile, get_player_profile, get_league_profile]:
    assert callable(fn), f"{fn.__name__} not callable"
    assert inspect.iscoroutinefunction(fn), f"{fn.__name__} not async"

print("OK: All route functions verified")

# Check error types accessible from football_api
from services.football_api import (
    APIError, APIRateLimitError, APITimeoutError, APIConnectionError, APIInvalidResponseError,
)
assert issubclass(APIRateLimitError, APIError)
assert issubclass(APITimeoutError, APIError)
assert issubclass(APIConnectionError, APIError)
assert issubclass(APIInvalidResponseError, APIError)

print("OK: Error types accessible")

# Check provider is a valid Provider
from providers.api_football.client import ApiFootballProvider
from providers.base import Provider
assert issubclass(ApiFootballProvider, Provider)
p = ApiFootballProvider()
assert p.name == "api_football"
print("OK: ApiFootballProvider is valid Provider")

# Check registry can be built with the provider
from providers.registry import ProviderRegistry
reg = ProviderRegistry({"api_football": p})
assert reg.has_provider("api_football")
print("OK: ProviderRegistry works")

print("\nAll route compatibility checks passed!")
