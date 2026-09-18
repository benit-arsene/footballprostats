"""Provider registry — manages provider instances and entity-to-provider mapping."""

from __future__ import annotations

import logging
from typing import Any

from providers.base import Provider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry that maps entity types to primary/fallback providers.

    Selection strategy: each entity type can have a primary and optional
    fallback provider. When fetching data, the registry tries the primary
    provider first; if it fails, it falls back to the fallback provider.

    Configuration lives in providers/config.py (PROVIDER_SELECTION).
    """

    def __init__(self, providers: dict[str, Provider]) -> None:
        """Initialize registry with provider instances keyed by provider name."""
        self._providers: dict[str, Provider] = providers

    def get_provider(self, name: str) -> Provider:
        """Get a provider by name."""
        provider = self._providers.get(name)
        if provider is None:
            raise ValueError(f"Unknown provider: {name}")
        return provider

    def list_providers(self) -> list[str]:
        """List registered provider names."""
        return list(self._providers.keys())

    async def fetch(
        self,
        entity_type: str,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Fetch data via the designated provider for an entity type.

        entity_type: e.g. 'competition', 'team', 'match', 'standings'
        method: provider method name to call, e.g. 'get_team', 'get_standings'
        *args, **kwargs: passed to the provider method

        Tries primary provider first; falls back to fallback provider on failure.
        Returns None or empty list if all providers fail (caller handles it).
        """
        from providers.config import PROVIDER_SELECTION

        selection = PROVIDER_SELECTION.get(entity_type, {})
        primary_name = selection.get("primary")
        fallback_name = selection.get("fallback")

        providers_to_try: list[str] = []
        if primary_name:
            providers_to_try.append(primary_name)
        if fallback_name and fallback_name != primary_name:
            providers_to_try.append(fallback_name)

        # If no explicit selection, try all providers
        if not providers_to_try:
            providers_to_try = self.list_providers()

        last_error: Exception | None = None
        for provider_name in providers_to_try:
            provider = self._providers.get(provider_name)
            if provider is None:
                continue
            try:
                method_call = getattr(provider, method)
                return await method_call(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    "Provider %s failed for %s.%s: %s",
                    provider_name, entity_type, method, e,
                )

        if last_error:
            logger.error("All providers failed for %s.%s: %s", entity_type, method, last_error)
        return None

    def has_provider(self, name: str) -> bool:
        """Check if a provider is registered."""
        return name in self._providers
