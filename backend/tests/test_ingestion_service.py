"""Focused tests for backend/ingestion/service.py upsert foundation.

All tests use mocked AsyncSession — no database, no external APIs.
"""

import asyncio
from datetime import date
from unittest import mock

import pytest

import ingestion.service as svc
from ingestion.service import (
    upsert_entity,
    upsert_external_id,
    upsert_competition,
    upsert_season,
    upsert_team,
    upsert_player,
    upsert_match,
)


# ─── Mock helpers ───────────────────────────────────────────────────────


class _MockResult:
    def __init__(self, row):
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class _MockSession:
    """SQLAlchemy 2.0 AsyncSession stand-in: add() is sync, execute/flush awaited."""

    def __init__(self, existing_row=None):
        self.existing_row = existing_row
        self.added = []
        self.flushed = 0

    def add(self, instance):
        self.added.append(instance)

    async def execute(self, stmt):
        return _MockResult(self.existing_row)

    async def flush(self):
        self.flushed += 1


class _MockModel:
    """Stand-in for a SQLAlchemy declarative model with class-level columns."""

    __tablename__ = "test_model"

    id = mock.Mock(name="id")
    slug = mock.Mock(name="slug")
    competition_id = mock.Mock(name="competition_id")
    label = mock.Mock(name="label")
    name = mock.Mock(name="name")
    country = mock.Mock(name="country")
    availability_status = mock.Mock(name="availability_status")
    entity_type = mock.Mock(name="entity_type")
    provider = mock.Mock(name="provider")
    external_id = mock.Mock(name="external_id")
    team_id = mock.Mock(name="team_id")
    player_id = mock.Mock(name="player_id")
    match_id = mock.Mock(name="match_id")

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _run_async(coro):
    return asyncio.run(coro)


# ─── Tests ─────────────────────────────────────────────────────────────


class TestUpsertEntityInsert:
    def test_insert_creates_new_row(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_entity(
                    session,
                    _MockModel,
                    conflict_keys={"slug": "arsenal"},
                    values={"name": "Arsenal"},
                    preserve_existing=True,
                )
            )

        assert created is True
        assert len(session.added) == 1
        assert session.flushed == 1
        added = session.added[0]
        assert added.slug == "arsenal"
        assert added.name == "Arsenal"

    def test_insert_with_none_optional_fields(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_entity(
                    session,
                    _MockModel,
                    conflict_keys={"slug": "arsenal"},
                    values={"name": "Arsenal", "country": None},
                    preserve_existing=True,
                )
            )

        assert created is True
        added = session.added[0]
        assert added.slug == "arsenal"
        assert added.name == "Arsenal"
        assert added.country is None


class TestUpsertEntityUpdate:
    def test_update_changes_provided_fields(self):
        existing = _MockModel(slug="arsenal", name="Old Name", country="England")
        session = _MockSession(existing_row=existing)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_entity(
                    session,
                    _MockModel,
                    conflict_keys={"slug": "arsenal"},
                    values={"name": "Arsenal FC"},
                    preserve_existing=True,
                )
            )

        assert created is False
        assert entity.name == "Arsenal FC"
        assert entity.country == "England"
        assert session.flushed == 1
        assert len(session.added) == 0

    def test_update_preserves_existing_when_incoming_none(self):
        existing = _MockModel(slug="arsenal", name="Arsenal FC", country="England")
        session = _MockSession(existing_row=existing)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_entity(
                    session,
                    _MockModel,
                    conflict_keys={"slug": "arsenal"},
                    values={"name": "Arsenal FC", "country": None},
                    preserve_existing=True,
                )
            )

        assert created is False
        assert entity.country == "England"

    def test_update_overwrites_when_preserve_existing_false(self):
        existing = _MockModel(slug="arsenal", name="Arsenal FC", country="England")
        session = _MockSession(existing_row=existing)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_entity(
                    session,
                    _MockModel,
                    conflict_keys={"slug": "arsenal"},
                    values={"name": "Arsenal FC", "country": None},
                    preserve_existing=False,
                )
            )

        assert entity.country is None

    def test_duplicate_conflict_key_does_not_insert(self):
        existing = _MockModel(slug="arsenal", name="First")
        session = _MockSession(existing_row=existing)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            _, created1 = _run_async(
                upsert_entity(
                    session,
                    _MockModel,
                    conflict_keys={"slug": "arsenal"},
                    values={"name": "First"},
                )
            )
            assert created1 is False

            entity2, created2 = _run_async(
                upsert_entity(
                    session,
                    _MockModel,
                    conflict_keys={"slug": "arsenal"},
                    values={"name": "Second"},
                )
            )
            assert created2 is False
            assert entity2.name == "Second"
            assert len(session.added) == 0


class TestUpsertEntityCompositeKey:
    def test_composite_key_insert(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_entity(
                    session,
                    _MockModel,
                    conflict_keys={"competition_id": 1, "label": "2026/2027"},
                    values={"availability_status": "imported"},
                )
            )

        assert created is True
        added = session.added[0]
        assert added.competition_id == 1
        assert added.label == "2026/2027"

    def test_composite_key_update(self):
        existing = _MockModel(
            competition_id=1, label="2026/2027", availability_status="not_imported"
        )
        session = _MockSession(existing_row=existing)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_entity(
                    session,
                    _MockModel,
                    conflict_keys={"competition_id": 1, "label": "2026/2027"},
                    values={"availability_status": "imported"},
                )
            )

        assert created is False
        assert entity.availability_status == "imported"


class TestUpsertExternalId:
    def test_create_external_id_mapping(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_external_id(
                    session,
                    entity_type="team",
                    provider="api_football",
                    external_id="42",
                    internal_id=100,
                    entity_column="team_id",
                )
            )

        assert created is True
        assert len(session.added) == 1
        added = session.added[0]
        assert added.entity_type == "team"
        assert added.provider == "api_football"
        assert added.external_id == "42"
        assert added.team_id == 100

    def test_external_id_preserves_internal_id(self):
        existing = _MockModel(
            entity_type="team",
            provider="api_football",
            external_id="42",
            team_id=999,
        )
        session = _MockSession(existing_row=existing)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_external_id(
                    session,
                    entity_type="team",
                    provider="api_football",
                    external_id="42",
                    internal_id=100,
                    entity_column="team_id",
                )
            )

        assert created is False
        assert entity.team_id == 999

    def test_external_id_match_column(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.select") as mock_select:
            mock_chain = mock.MagicMock()
            mock_select.return_value = mock_chain
            mock_chain.where.return_value = mock_chain

            entity, created = _run_async(
                upsert_external_id(
                    session,
                    entity_type="match",
                    provider="football_data",
                    external_id="101",
                    internal_id=500,
                    entity_column="match_id",
                )
            )

        assert created is True
        added = session.added[0]
        assert added.match_id == 500
        assert added.team_id is None
        assert added.player_id is None


class TestTypeSafeWrappers:
    def test_upsert_competition(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.upsert_entity", new=mock.AsyncMock()) as mock_upsert:
            mock_upsert.return_value = (mock.Mock(id=1), True)
            entity, created = _run_async(
                svc.upsert_competition(
                    session,
                    slug="premier-league",
                    name="Premier League",
                    country="England",
                )
            )

        assert created is True
        mock_upsert.assert_called_once()
        kwargs = mock_upsert.call_args.kwargs
        assert kwargs["conflict_keys"] == {"slug": "premier-league"}
        assert kwargs["values"]["name"] == "Premier League"
        assert kwargs["values"]["country"] == "England"

    def test_upsert_competition_omits_none_fields(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.upsert_entity", new=mock.AsyncMock()) as mock_upsert:
            mock_upsert.return_value = (mock.Mock(id=1), True)
            _run_async(
                svc.upsert_competition(
                    session,
                    slug="premier-league",
                    name="Premier League",
                    country=None,
                    logo_url=None,
                )
            )

        kwargs = mock_upsert.call_args.kwargs
        assert "country" not in kwargs["values"]
        assert "logo_url" not in kwargs["values"]

    def test_upsert_season_composite_key(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.upsert_entity", new=mock.AsyncMock()) as mock_upsert:
            mock_upsert.return_value = (mock.Mock(id=1), True)
            _run_async(
                svc.upsert_season(
                    session,
                    competition_id=1,
                    label="2026/2027",
                    availability_status="imported",
                )
            )

        kwargs = mock_upsert.call_args.kwargs
        assert kwargs["conflict_keys"] == {"competition_id": 1, "label": "2026/2027"}
        assert kwargs["values"]["availability_status"] == "imported"

    def test_upsert_team(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.upsert_entity", new=mock.AsyncMock()) as mock_upsert:
            mock_upsert.return_value = (mock.Mock(id=1), True)
            _run_async(
                svc.upsert_team(
                    session,
                    slug="arsenal",
                    name="Arsenal",
                    short_name="ARS",
                    crest_url="https://example.com/arsenal.png",
                )
            )

        kwargs = mock_upsert.call_args.kwargs
        assert kwargs["conflict_keys"] == {"slug": "arsenal"}
        assert kwargs["values"]["short_name"] == "ARS"
        assert kwargs["values"]["crest_url"] == "https://example.com/arsenal.png"

    def test_upsert_player(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.upsert_entity", new=mock.AsyncMock()) as mock_upsert:
            mock_upsert.return_value = (mock.Mock(id=1), True)
            _run_async(
                svc.upsert_player(
                    session,
                    slug="bukayo-saka",
                    name="Bukayo Saka",
                    position="Attack",
                    number=7,
                    nationality="England",
                )
            )

        kwargs = mock_upsert.call_args.kwargs
        assert kwargs["conflict_keys"] == {"slug": "bukayo-saka"}
        assert kwargs["values"]["position"] == "Attack"
        assert kwargs["values"]["number"] == 7

    def test_upsert_match_does_not_touch_external_ids(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.upsert_entity", new=mock.AsyncMock()) as mock_upsert:
            mock_upsert.return_value = (mock.Mock(id=1), True)
            _run_async(
                svc.upsert_match(
                    session,
                    slug="arsenal-chelsea-2026-08-22",
                    home_team_id=1,
                    away_team_id=2,
                    date=date(2026, 8, 22),
                    competition_id=39,
                    season_id=5,
                    status="scheduled",
                    home_score=0,
                    away_score=0,
                )
            )

        kwargs = mock_upsert.call_args.kwargs
        assert kwargs["conflict_keys"] == {"slug": "arsenal-chelsea-2026-08-22"}
        assert kwargs["values"]["home_team_id"] == 1
        assert kwargs["values"]["away_team_id"] == 2
        assert kwargs["values"]["competition_id"] == 39
        assert kwargs["values"]["season_id"] == 5


class TestMatchIdentityBoundary:
    def test_match_upsert_uses_internal_slug_not_provider_id(self):
        session = _MockSession(existing_row=None)

        with mock.patch("ingestion.service.upsert_entity", new=mock.AsyncMock()) as mock_upsert:
            mock_upsert.return_value = (mock.Mock(id=42), True)
            _run_async(
                svc.upsert_match(
                    session,
                    slug="arsenal-chelsea-2026-08-22",
                    home_team_id=1,
                    away_team_id=2,
                    date=date(2026, 8, 22),
                )
            )

        kwargs = mock_upsert.call_args.kwargs
        assert kwargs["conflict_keys"] == {"slug": "arsenal-chelsea-2026-08-22"}

    def test_external_id_match_mapping_separate_from_match_row(self):
        session = _MockSession(existing_row=None)

        ext_mock = mock.Mock()
        ext_mock.entity_type = "match"
        ext_mock.provider = "football_data"
        ext_mock.external_id = "101"
        ext_mock.match_id = 42
        ext_mock.team_id = None
        ext_mock.player_id = None

        with mock.patch.object(svc, "upsert_external_id", new=mock.AsyncMock()) as mock_ext:
            mock_ext.return_value = (ext_mock, True)
            _run_async(
                svc.upsert_external_id(
                    session,
                    entity_type="match",
                    provider="football_data",
                    external_id="101",
                    internal_id=42,
                    entity_column="match_id",
                )
            )

        assert mock_ext.call_args is not None
        kwargs = mock_ext.call_args.kwargs
        assert kwargs["entity_type"] == "match"
        assert kwargs["external_id"] == "101"
        assert kwargs["internal_id"] == 42
        assert kwargs["entity_column"] == "match_id"
