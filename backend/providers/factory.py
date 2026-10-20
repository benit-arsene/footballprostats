"""Provider factory — builds a ProviderRegistry with all available providers.

football-data.org is registered only when FOOTBALLDATA_KEY is set.
API-Football is always registered (its key is required for the app to function).
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv()

from providers.api_football.client import ApiFootballProvider
from providers.base import Provider
from providers.config import AVAILABLE_PROVIDERS, PROVIDER_SELECTION
from providers.football_data.client import FootballDataProvider
from providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


def build_provider_registry() -> ProviderRegistry:
    """Build a ProviderRegistry with all available providers.

    football-data.org is only registered when FOOTBALLDATA_KEY is set.
    Missing credentials do not raise — the provider is simply omitted.
    """
    providers: dict[str, Provider] = {}

    # API-Football — always available (required for the app)
    try:
        providers["api_football"] = ApiFootballProvider()
    except Exception as e:
        logger.error("Failed to initialize API-Football provider: %s", e)

    # football-data.org — only if credentials are present
    if os.getenv("FOOTBALLDATA_KEY"):
        try:
            providers["football_data"] = FootballDataProvider()
            logger.info("football-data.org provider registered")
        except Exception as e:
            logger.warning("Failed to initialize football-data.org provider: %s", e)
    else:
        logger.debug("FOOTBALLDATA_KEY not set; football-data.org provider not registered")

    return ProviderRegistry(providers)


def get_available_providers() -> list[str]:
    """Return the list of provider names that are currently registered."""
    registry = build_provider_registry()
    return registry.list_providers()