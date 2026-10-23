"""Tests for provider competition-ID registration and extraction.

No database connection is opened and no provider is called. The tests pin the
canonical identifier format per provider, the conflict rules of the registration
helper, and that what gets registered is exactly what fixture ingestion later
resolves.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models.external_id import ExternalId
from ingestion.fixtures import _resolve_provider_competition_id
from ingestion.service import (
    canonical_competition_external_id,
    register_competition_mapping,
)
from providers.api_football.ids import canonical_league_id
from providers.football_data.ids import (
    canonical_competition_code,
    extract_competition_external_ids,
)


# ─── Fake session ───────────────────────────────────────────────────────


class _ScalarResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return _ScalarResult(self._rows)

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _FakeSession:
    """In-memory stand-in for external_ids reads/writes."""

    def __init__(self, rows=()):
        self.rows = list(rows)
        self.added = []
        self.flushes = 0

    def add(self, instance):
        self.added.append(instance)
        self.rows.append(instance)

    async def flush(self):
        self.flushes += 1

    async def execute(self, stmt):
        criteria = {}
        for key, value in stmt.compile().params.items():
            name = key.rsplit("_", 1)[0]
            if name == "param":
                continue
            criteria[name] = value

        selected = [
            row
            for row in self.rows
            if all(
                not hasattr(row, name) or getattr(row, name) == value
                for name, value in criteria.items()
            )
        ]
        return _Result(selected)


def _run(coro):
    return asyncio.run(coro)


# ─── Extraction: canonical provider identifier ─────────────────────────


class TestCompetitionExtraction:
    def test_premier_league_extracts_code(self):
        payload = {"id": 2021, "name": "Premier League", "code": "PL"}
        assert extract_competition_external_ids(payload) == [("football_data", "PL")]

    def test_la_liga_extracts_code(self):
        payload = {"id": 2014, "name": "Primera Division", "code": "PD"}
        assert extract_competition_external_ids(payload) == [("football_data", "PD")]

    def test_code_is_normalised(self):
        assert extract_competition_external_ids({"code": " pl "}) == [
            ("football_data", "PL")
        ]

    def test_numeric_id_is_not_used_as_the_mapping(self):
        """The provider's numeric id cannot satisfy fixture requests."""
        assert extract_competition_external_ids({"id": 2021, "code": None}) == []
        assert extract_competition_external_ids({"id": 2021}) == []

    def test_missing_payload_or_blank_code(self):
        assert extract_competition_external_ids({}) == []
        assert extract_competition_external_ids(None) == []
        assert extract_competition_external_ids({"code": "   "}) == []


# ─── Canonical identifier per provider ─────────────────────────────────


class TestCanonicalIdentifiers:
    def test_football_data_stores_competition_codes(self):
        assert canonical_competition_external_id("football_data", "pl") == "PL"
        assert canonical_competition_external_id("football_data", " PD ") == "PD"
        assert canonical_competition_code("CL") == "CL"

    def test_football_data_rejects_numeric_ids(self):
        with pytest.raises(ValueError, match="not a supported football-data.org competition code"):
            canonical_competition_external_id("football_data", "2021")
        # API-Football's league id is not football-data.org's identifier either.
        with pytest.raises(ValueError, match="not a supported football-data.org competition code"):
            canonical_competition_external_id("football_data", "39")

    def test_api_football_stores_numeric_league_ids(self):
        assert canonical_competition_external_id("api_football", 39) == "39"
        assert canonical_competition_external_id("api_football", "140") == "140"
        assert canonical_league_id(39) == "39"

    def test_api_football_rejects_codes(self):
        with pytest.raises(ValueError, match="not a numeric API-Football league id"):
            canonical_competition_external_id("api_football", "PL")

    def test_unknown_provider_is_rejected(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            canonical_competition_external_id("other_provider", "X")


# ─── Registration ──────────────────────────────────────────────────────


class TestCompetitionMappingRegistration:
    def test_premier_league_code_is_registered(self):
        session = _FakeSession()
        row, created = _run(
            register_competition_mapping(session, "football_data", 7, "PL")
        )

        assert created is True
        assert row.entity_type == "competition"
        assert row.provider == "football_data"
        assert row.external_id == "PL"
        # The internal competition id is only ever the foreign key value.
        assert row.competition_id == 7
        assert session.added == [row]

    def test_la_liga_code_is_registered(self):
        session = _FakeSession()
        row, created = _run(
            register_competition_mapping(session, "football_data", 2, "PD")
        )

        assert created is True
        assert row.external_id == "PD"
        assert row.competition_id == 2

    def test_api_football_numeric_mapping_is_unchanged(self):
        session = _FakeSession()
        row, created = _run(
            register_competition_mapping(session, "api_football", 1, 39)
        )

        assert created is True
        assert row.external_id == "39"
        assert row.competition_id == 1

    def test_existing_exact_mapping_is_idempotent(self):
        existing = ExternalId(
            id=5,
            entity_type="competition",
            provider="football_data",
            external_id="PL",
            competition_id=1,
        )
        session = _FakeSession([existing])

        row, created = _run(
            register_competition_mapping(session, "football_data", 1, "PL")
        )

        assert row is existing
        assert created is False
        assert session.added == []

    def test_unlinked_row_is_bound_to_the_competition(self):
        existing = ExternalId(
            id=5,
            entity_type="competition",
            provider="football_data",
            external_id="PL",
            competition_id=None,
        )
        session = _FakeSession([existing])

        row, created = _run(
            register_competition_mapping(session, "football_data", 1, "PL")
        )

        assert row is existing
        assert created is False
        assert row.competition_id == 1
        assert session.added == []

    def test_external_id_mapped_to_another_competition_conflicts(self):
        session = _FakeSession(
            [
                ExternalId(
                    id=5,
                    entity_type="competition",
                    provider="football_data",
                    external_id="PL",
                    competition_id=2,
                )
            ]
        )

        with pytest.raises(ValueError, match="already mapped to internal competition 2"):
            _run(register_competition_mapping(session, "football_data", 1, "PL"))

        assert session.added == []

    def test_second_mapping_for_same_competition_conflicts(self):
        session = _FakeSession(
            [
                ExternalId(
                    id=5,
                    entity_type="competition",
                    provider="football_data",
                    external_id="PD",
                    competition_id=1,
                )
            ]
        )

        with pytest.raises(ValueError, match="already has football_data competition mapping"):
            _run(register_competition_mapping(session, "football_data", 1, "PL"))

        assert session.added == []

    def test_stale_numeric_mapping_blocks_a_code_registration(self):
        """A stored numeric id must be corrected, not shadowed by a code."""
        session = _FakeSession(
            [
                ExternalId(
                    id=5,
                    entity_type="competition",
                    provider="football_data",
                    external_id="2021",
                    competition_id=1,
                )
            ]
        )

        with pytest.raises(ValueError, match="already has football_data competition mapping"):
            _run(register_competition_mapping(session, "football_data", 1, "PL"))

        assert session.added == []

    def test_mapping_from_another_provider_does_not_satisfy_registration(self):
        session = _FakeSession(
            [
                ExternalId(
                    id=5,
                    entity_type="competition",
                    provider="api_football",
                    external_id="39",
                    competition_id=1,
                )
            ]
        )

        row, created = _run(
            register_competition_mapping(session, "football_data", 1, "PL")
        )

        assert created is True
        assert row.external_id == "PL"
        providers = {r.provider for r in session.rows}
        assert providers == {"api_football", "football_data"}

    def test_registration_of_unsupported_code_fails(self):
        session = _FakeSession()
        with pytest.raises(ValueError, match="not a supported football-data.org competition code"):
            _run(register_competition_mapping(session, "football_data", 1, "2021"))
        assert session.added == []


# ─── Registered mappings match what fixture ingestion resolves ─────────


class TestRegisteredMappingsResolve:
    def test_football_data_mapping_is_resolved_by_fixture_ingestion(self):
        session = _FakeSession()
        _run(register_competition_mapping(session, "football_data", 2, "PD"))

        league_reference = _run(
            _resolve_provider_competition_id(session, "football_data", 2)
        )
        assert league_reference == "PD"

    def test_api_football_mapping_is_resolved_by_fixture_ingestion(self):
        session = _FakeSession()
        _run(register_competition_mapping(session, "api_football", 1, 39))

        league_reference = _run(
            _resolve_provider_competition_id(session, "api_football", 1)
        )
        assert league_reference == 39

    def test_extraction_output_registers_and_resolves(self):
        pairs = extract_competition_external_ids({"id": 2021, "code": "PL"})
        assert pairs == [("football_data", "PL")]
        provider, external_id = pairs[0]

        session = _FakeSession()
        _run(register_competition_mapping(session, provider, 1, external_id))

        assert (
            _run(_resolve_provider_competition_id(session, provider, 1)) == "PL"
        )

    def test_providers_cannot_be_confused(self):
        session = _FakeSession()
        _run(register_competition_mapping(session, "football_data", 2, "PD"))

        with pytest.raises(ValueError, match="No api_football competition mapping"):
            _run(_resolve_provider_competition_id(session, "api_football", 2))

        assert (
            _run(_resolve_provider_competition_id(session, "football_data", 2))
            == "PD"
        )


class TestRegistrationScriptConstants:
    def test_register_laliga_stores_a_competition_code(self):
        import register_laliga as script

        assert script.PROVIDER == "football_data"
        assert script.EXTERNAL_ID == "PD"
        assert (
            canonical_competition_external_id(script.PROVIDER, script.EXTERNAL_ID)
            == "PD"
        )
