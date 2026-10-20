"""Focused tests for refresh_current module (config/error paths)."""

import os
from unittest import mock
import pytest


def test_missing_footballdata_key_returns_failure(monkeypatch):
    monkeypatch.delenv("FOOTBALLDATA_KEY", raising=False)
    monkeypatch.setenv("FOOTBALLDATA_KEY", "")
    # Rebuild registry without key by patching build_provider_registry
    import ingestion.refresh_current as rc
    with mock.patch("ingestion.refresh_current.build_provider_registry") as br:
        reg = mock.MagicMock()
        reg.list_providers.return_value = ["api_football"]
        br.return_value = reg
        # route_provider will select api_football (not football_data) -> returns 1
        res = __import__("asyncio").run(rc.run())
        assert res == 1
