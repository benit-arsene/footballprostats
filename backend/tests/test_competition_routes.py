"""Route tests for the database-first competition read endpoints.

These tests use a mocked AsyncSession: no PostgreSQL connection is opened, no
external provider is called, and no data is written. They pin:

  * the JSON shapes the frontend consumes,
  * internal-id vs provider-id handling (including the ambiguous case),
  * missing competition / season / dataset behaviour,
  * that the module has no provider path at all.
"""

import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_season_year
from db.models.competition import Competition
from db.models.external_id import ExternalId
from db.models.match import Match
from db.models.player import Player
from db.models.player_season_stat import PlayerSeasonStat
from db.models.season import Season
from db.models.standing_row import StandingRow as StandingRowModel
from db.models.standing_snapshot import StandingSnapshot
from db.models.team import Team
from db.models.venue import Venue
from routes import competitions as comp


# ─── Fakes ───────────────────────────────────────────────────────────────


class _ScalarResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return _ScalarResult(self._rows)

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


# Parameters that are range/limit predicates, not equality filters.
_IGNORED_PARAMS = {"date", "param"}


def _filter(rows, stmt):
    """Apply the equality predicates a real database would apply.

    Range predicates (``date >= today``) and limits stay in SQL; the canned
    rows already represent a valid database result for those. Queries that
    select several entities are filtered on their first (primary) entity.
    """
    criteria = {}
    for key, value in stmt.compile().params.items():
        name = key.rsplit("_", 1)[0]
        if name in _IGNORED_PARAMS:
            continue
        criteria[name] = value

    selected = []
    for row in rows:
        entity = row[0] if isinstance(row, tuple) else row
        matches = True
        for name, value in criteria.items():
            if not hasattr(entity, name):
                continue
            if getattr(entity, name) != value:
                matches = False
                break
        if matches:
            selected.append(row)
    return selected


class _FakeSession:
    def __init__(self, data):
        self.data = data

    async def execute(self, stmt):
        sql = str(stmt)
        for table, rows in self.data.items():
            if f"FROM {table}" in sql:
                return _Result(_filter(rows, stmt))
        raise AssertionError(f"unexpected query in test: {sql}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def _session_factory(data):
    def factory():
        return _FakeSession(data)

    return factory


# ─── Stored fixtures ─────────────────────────────────────────────────────


CURRENT_LABEL = f"{get_season_year()}/{get_season_year() + 1}"


def _competition() -> Competition:
    return Competition(
        id=1,
        name="Premier League",
        slug="premier-league-39",
        country="England",
        logo_url="https://example.com/pl.png",
    )


def _la_liga() -> Competition:
    return Competition(
        id=2,
        name="La Liga",
        slug="laliga",
        country="Spain",
        logo_url=None,
    )


def _champions_league() -> Competition:
    return Competition(
        id=3,
        name="Champions League",
        slug="champions-league-2",
        country="Europe",
        logo_url=None,
    )


def _season(competition_id: int = 1) -> Season:
    return Season(
        id=5,
        competition_id=competition_id,
        label=CURRENT_LABEL,
        availability_status="imported",
    )


def _teams() -> list[Team]:
    return [
        Team(id=10, name="Arsenal", slug="arsenal-42", crest_url="https://example.com/arsenal.png"),
        Team(id=11, name="Chelsea", slug="chelsea-49", crest_url=None),
    ]


def _snapshots(season_id: int = 5) -> list[StandingSnapshot]:
    return [
        StandingSnapshot(
            id=7,
            season_id=season_id,
            label="old snapshot",
            snapshot_date=datetime(2026, 9, 1, 12, 0),
        ),
        StandingSnapshot(
            id=8,
            season_id=season_id,
            label="latest snapshot",
            snapshot_date=datetime(2026, 10, 1, 12, 0),
        ),
    ]


def _standing_rows(snapshot_id: int = 8) -> list[StandingRowModel]:
    return [
        StandingRowModel(
            id=100,
            standing_snapshot_id=snapshot_id,
            team_id=10,
            position=1,
            played=9,
            won=7,
            drawn=1,
            lost=1,
            goals_for=21,
            goals_against=8,
            goal_difference=13,
            points=22,
            form="WWDLW",
        ),
        StandingRowModel(
            id=101,
            standing_snapshot_id=snapshot_id,
            team_id=11,
            position=2,
            played=9,
            won=6,
            drawn=1,
            lost=2,
            goals_for=18,
            goals_against=11,
            goal_difference=7,
            points=19,
            form="W,D,L,W,W",
        ),
    ]


def _players() -> list[Player]:
    return [
        Player(
            id=20,
            name="Bukayo Saka",
            slug="bukayo-saka-42",
            position="Attacker",
            number=7,
            nationality="England",
        ),
        Player(
            id=21,
            name="Cole Palmer",
            slug="cole-palmer-49",
            position="Midfielder",
            number=10,
            nationality=None,
        ),
    ]


def _season_stats(season_id: int = 5) -> list[PlayerSeasonStat]:
    return [
        PlayerSeasonStat(
            id=1, player_id=20, season_id=season_id, team_id=10, goals=9, assists=4
        ),
        # Same player, second club in the season — must not be listed twice.
        PlayerSeasonStat(
            id=2, player_id=20, season_id=season_id, team_id=11, goals=9, assists=4
        ),
        PlayerSeasonStat(
            id=3, player_id=21, season_id=season_id, team_id=11, goals=6, assists=7
        ),
    ]


def _matches() -> list[tuple]:
    teams = {team.id: team for team in _teams()}
    venue = Venue(id=1, name="Emirates Stadium")
    scheduled = Match(
        id=501,
        slug="arsenal-vs-chelsea-501",
        competition_id=1,
        season_id=5,
        home_team_id=10,
        away_team_id=11,
        venue_id=1,
        date=date.today() + timedelta(days=2),
        kickoff_time=time(15, 0),
        status="scheduled",
        minute=None,
        home_score=0,
        away_score=0,
    )
    finished = Match(
        id=499,
        slug="chelsea-vs-arsenal-499",
        competition_id=1,
        season_id=5,
        home_team_id=11,
        away_team_id=10,
        venue_id=None,
        date=date.today() - timedelta(days=3),
        kickoff_time=time(17, 30),
        status="finished",
        minute=None,
        home_score=1,
        away_score=2,
    )
    return [
        (finished, teams[11], teams[10], None),
        (scheduled, teams[10], teams[11], venue),
    ]


def _data(**overrides) -> dict:
    """Canned query results keyed by the primary table of each query."""
    data = {
        "competitions": [_competition()],
        "external_ids": [],
        "seasons": [_season()],
        "standing_rows": [
            (row, team, snapshot)
            for row in _standing_rows()
            for team in _teams()
            if team.id == row.team_id
            for snapshot in _snapshots()
            if snapshot.id == row.standing_snapshot_id
        ],
        "player_season_stats": [
            (stat, player, team)
            for stat in _season_stats()
            for player in _players()
            if player.id == stat.player_id
            for team in _teams()
            if team.id == stat.team_id
        ],
        "matches": _matches(),
    }
    data.update(overrides)
    return data


@pytest.fixture
def stored(monkeypatch):
    monkeypatch.setattr(comp, "async_session", _session_factory(_data()))
    return _data()


# ─── Hub ─────────────────────────────────────────────────────────────────


def test_hub_serves_stored_data(stored):
    profile = asyncio.run(comp.get_competition_profile(1))

    assert profile.id == 1  # internal competition id, not provider id 39
    assert profile.name == "Premier League"
    assert profile.slug == "premier-league-39"
    assert profile.country == "England"
    assert profile.logo_url == "https://example.com/pl.png"
    assert profile.season == CURRENT_LABEL

    assert len(profile.standings) == 2
    first = profile.standings[0]
    assert first.position == 1
    assert first.team.id == 10
    assert first.team.name == "Arsenal"
    assert (first.played, first.won, first.drawn, first.lost) == (9, 7, 1, 1)
    assert (first.gf, first.ga, first.gd, first.points) == (21, 8, 13, 22)
    assert first.form == ["W", "W", "D", "L", "W"]
    assert profile.standings[1].form == ["W", "D", "L", "W", "W"]

    # One row per player, using stored goals/assists.
    assert [scorer.player.id for scorer in profile.top_scorers] == [20, 21]
    assert profile.top_scorers[0].goals == 9
    assert profile.top_scorers[0].assists == 4
    assert profile.top_scorers[0].team.id == 10
    assert profile.top_scorers[1].player.nationality == ""

    # Only the stored scheduled match is a fixture.
    assert [match.id for match in profile.fixtures] == [501]
    fixture = profile.fixtures[0]
    assert fixture.status.value == "scheduled"
    assert fixture.league.id == 1
    assert fixture.league.slug == "premier-league-39"
    assert fixture.home_team.slug == "arsenal-42"
    assert fixture.away_team.crest_url == ""
    assert fixture.venue == "Emirates Stadium"
    assert fixture.kickoff_time == "15:00"
    assert fixture.date == (date.today() + timedelta(days=2)).isoformat()


def test_hub_resolves_provider_id_through_external_ids(monkeypatch):
    """Frontend URLs carry provider ids (epl-39); external_ids maps them."""
    data = _data(
        external_ids=[
            ExternalId(
                id=1,
                entity_type="competition",
                provider="api_football",
                external_id="39",
                competition_id=1,
            )
        ]
    )
    monkeypatch.setattr(comp, "async_session", _session_factory(data))

    profile = asyncio.run(comp.get_competition_profile(39))

    assert profile.id == 1
    assert profile.name == "Premier League"


def test_internal_id_wins_when_only_internal_row_matches(monkeypatch):
    data = _data(competitions=[_competition(), _la_liga()], seasons=[_season(2)])
    monkeypatch.setattr(comp, "async_session", _session_factory(data))

    profile = asyncio.run(comp.get_competition_profile(2))

    assert profile.id == 2
    assert profile.name == "La Liga"


def test_ambiguous_id_is_rejected(monkeypatch):
    """Internal id 2 (La Liga) and provider id 2 (Champions League) collide."""
    data = _data(
        competitions=[_competition(), _la_liga(), _champions_league()],
        external_ids=[
            ExternalId(
                id=2,
                entity_type="competition",
                provider="api_football",
                external_id="2",
                competition_id=3,
            )
        ],
    )
    monkeypatch.setattr(comp, "async_session", _session_factory(data))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(comp.get_competition_profile(2))

    assert exc.value.status_code == 409
    assert exc.value.detail["error"]["code"] == "AMBIGUOUS_COMPETITION_ID"


# ─── Individual endpoints ────────────────────────────────────────────────


def test_standings_endpoint_returns_frontend_shape(stored):
    rows = asyncio.run(comp.get_competition_standings(1))

    payload = rows[0].model_dump()
    assert set(payload) == {
        "position",
        "team",
        "played",
        "won",
        "drawn",
        "lost",
        "gf",
        "ga",
        "gd",
        "points",
        "form",
    }
    assert isinstance(payload["form"], list)
    assert payload["team"] == {
        "id": 10,
        "name": "Arsenal",
        "slug": "arsenal-42",
        "crest_url": "https://example.com/arsenal.png",
    }


def test_standings_use_latest_snapshot_that_has_rows(monkeypatch):
    """An empty newer snapshot must not wipe out the last valid table."""
    data = _data()
    data["standing_rows"] = [
        (row, team, snapshot)
        for row in _standing_rows(snapshot_id=7)
        for team in _teams()
        if team.id == row.team_id
        for snapshot in _snapshots()
        if snapshot.id == 7
    ]
    monkeypatch.setattr(comp, "async_session", _session_factory(data))

    rows = asyncio.run(comp.get_competition_standings(1))

    assert [row.position for row in rows] == [1, 2]
    assert rows[0].team.id == 10


def test_top_scorers_endpoint(stored):
    scorers = asyncio.run(comp.get_competition_top_scorers(1))

    assert len(scorers) == 2
    assert scorers[0].player.id == 20
    assert scorers[0].player.slug == "bukayo-saka-42"
    assert scorers[0].player.number == 7
    assert scorers[0].goals == 9
    assert scorers[0].team.name == "Arsenal"


def test_fixtures_endpoint_only_scheduled(stored):
    fixtures = asyncio.run(comp.get_competition_fixtures(1))

    assert [match.id for match in fixtures] == [501]
    assert all(match.status.value == "scheduled" for match in fixtures)


def test_results_endpoint_only_finished(stored):
    results = asyncio.run(comp.get_competition_results(1))

    assert [match.id for match in results] == [499]
    result = results[0]
    assert result.status.value == "finished"
    assert (result.home_score, result.away_score) == (1, 2)
    assert result.venue == ""
    assert result.league.id == 1


# ─── Missing data ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "endpoint",
    [
        comp.get_competition_profile,
        comp.get_competition_standings,
        comp.get_competition_top_scorers,
        comp.get_competition_fixtures,
        comp.get_competition_results,
    ],
)
def test_unknown_competition_returns_structured_404(stored, endpoint):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(endpoint(999))

    assert exc.value.status_code == 404
    assert exc.value.detail["error"]["code"] == "NOT_FOUND"
    assert "Competition 999" in exc.value.detail["error"]["message"]


def test_missing_season_returns_empty_datasets(monkeypatch):
    data = _data(seasons=[])
    monkeypatch.setattr(comp, "async_session", _session_factory(data))

    profile = asyncio.run(comp.get_competition_profile(1))
    assert profile.id == 1
    assert profile.season == CURRENT_LABEL  # response contract preserved
    assert profile.standings == []
    assert profile.top_scorers == []
    assert profile.fixtures == []

    assert asyncio.run(comp.get_competition_standings(1)) == []
    assert asyncio.run(comp.get_competition_top_scorers(1)) == []
    assert asyncio.run(comp.get_competition_fixtures(1)) == []
    assert asyncio.run(comp.get_competition_results(1)) == []


def test_missing_datasets_return_empty_lists(monkeypatch):
    data = _data(standing_rows=[], player_season_stats=[], matches=[])
    monkeypatch.setattr(comp, "async_session", _session_factory(data))

    profile = asyncio.run(comp.get_competition_profile(1))
    assert (profile.standings, profile.top_scorers, profile.fixtures) == ([], [], [])


# ─── No external provider path ───────────────────────────────────────────


def test_migrated_endpoints_make_no_provider_calls(monkeypatch, stored):
    """Replacing every provider entry point with a bomb must not matter."""
    from services import football_api

    def boom(*args, **kwargs):
        raise AssertionError("external provider was called from a read endpoint")

    for name in (
        "get_league",
        "get_standings",
        "get_top_scorers",
        "get_fixtures_by_date",
        "get_live_fixtures",
        "get_fixture",
    ):
        monkeypatch.setattr(football_api, name, boom)

    assert not hasattr(comp, "football_api")
    assert not hasattr(comp, "_registry")

    assert asyncio.run(comp.get_competition_profile(1)).name == "Premier League"
    assert asyncio.run(comp.get_competition_standings(1))
    assert asyncio.run(comp.get_competition_top_scorers(1))
    assert asyncio.run(comp.get_competition_fixtures(1))
    assert asyncio.run(comp.get_competition_results(1))


def test_route_paths_are_unchanged():
    from main import app

    paths = {route.path for route in app.routes}
    assert "/api/v1/competitions/{competition_id}" in paths
    assert "/api/v1/competitions/{competition_id}/standings" in paths
    assert "/api/v1/competitions/{competition_id}/top-scorers" in paths
    assert "/api/v1/competitions/{competition_id}/fixtures" in paths
    assert "/api/v1/competitions/{competition_id}/results" in paths


def test_hub_json_contract(monkeypatch, stored):
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as client:
        response = client.get("/api/v1/competitions/1")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "id",
        "name",
        "slug",
        "country",
        "logo_url",
        "season",
        "standings",
        "top_scorers",
        "fixtures",
    }
    assert body["standings"][0]["form"] == ["W", "W", "D", "L", "W"]
    assert body["standings"][0]["gd"] == 13
    assert body["fixtures"][0]["home_team"]["slug"] == "arsenal-42"
    assert body["fixtures"][0]["league"]["id"] == 1
    assert body["top_scorers"][0]["player"]["name"] == "Bukayo Saka"
