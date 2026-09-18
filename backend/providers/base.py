"""Provider abstraction — base class for all data providers."""

from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    """Abstract base class for all external data providers.

    Each provider implements methods to fetch specific entity types
    from an external API. All methods return canonical model instances
    from models.py or raw provider-specific dicts that will be passed
    through the normalization layer.

    Provider-specific response structures are never exposed outside
    the provider package.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier, e.g. 'api_football'."""

    @abstractmethod
    async def get_competition(self, competition_id: int) -> dict | None:
        """Fetch a single competition by ID. Returns raw provider response or None."""

    @abstractmethod
    async def get_competitions(self) -> list[dict]:
        """Fetch all available competitions. Returns list of raw responses."""

    @abstractmethod
    async def get_season(self, competition_id: int, season_label: str) -> dict | None:
        """Fetch a season for a competition. Returns raw provider response or None."""

    @abstractmethod
    async def get_team(self, team_id: int) -> dict | None:
        """Fetch team information. Returns raw provider response or None."""

    @abstractmethod
    async def get_team_players(self, team_id: int, season: int) -> list[dict]:
        """Fetch squad/players for a team. Returns list of raw player responses."""

    @abstractmethod
    async def get_player(self, player_id: int, season: int) -> dict | None:
        """Fetch player profile and stats. Returns raw provider response or None."""

    @abstractmethod
    async def get_fixtures(
        self,
        league_id: int | None = None,
        season: int | None = None,
        date: str | None = None,
        team_id: int | None = None,
    ) -> list[dict]:
        """Fetch fixtures with optional filters. Returns list of raw fixture responses."""

    @abstractmethod
    async def get_fixture(self, fixture_id: int) -> dict | None:
        """Fetch full fixture details. Returns raw fixture response or None."""

    @abstractmethod
    async def get_standings(self, league_id: int, season: int) -> list[dict]:
        """Fetch league standings. Returns list of raw standing rows."""

    @abstractmethod
    async def get_top_scorers(self, league_id: int, season: int) -> list[dict]:
        """Fetch top scorers. Returns list of raw scorer responses."""

    @abstractmethod
    async def search_team(self, name: str) -> list[dict]:
        """Search for teams by name. Returns list of raw team responses."""

    @abstractmethod
    def extract_external_ids(self, entity_type: str, data: Any) -> list[tuple[str, str]]:
        """Extract (provider_name, external_id) pairs from provider response data.

        entity_type: 'competition', 'season', 'team', 'player', 'match', etc.
        Returns list of (provider_name, external_id) tuples.
        """
