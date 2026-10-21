"""Tests for the image ingestion planner (no network, no database)."""

import asyncio
import pytest

from ingestion import ingest_images as ii


def _plan():
    return ii.plan_targets(
        players=[
            ii.PlayerTarget(player_id=1, api_player_id="1100", name="E. Haaland", has_photo=False),
            ii.PlayerTarget(player_id=2, api_player_id="1460", name="B. Saka", has_photo=True),
        ],
        teams=[
            ii.TeamTarget(team_id=1, api_team_id="33", name="Manchester United", has_crest=True),
            ii.TeamTarget(team_id=2, api_team_id="35", name="Bournemouth", has_crest=False),
        ],
    )


def test_default_arguments_plan_only():
    args = ii.parse_args([])
    assert args.apply is False
    assert args.fetch is False
    assert args.max_requests == ii.DEFAULT_MAX_REQUESTS
    assert args.targets == "both"


def test_fetch_requires_apply():
    with pytest.raises(SystemExit):
        ii.parse_args(["--fetch"])


def test_negative_request_budget_rejected():
    with pytest.raises(SystemExit):
        ii.parse_args(["--apply", "--fetch", "--max-requests", "-1"])


def test_budget_is_capped_at_daily_limit():
    budget = ii.RequestBudget(10_000)
    assert budget.limit == ii.DAILY_REQUEST_BUDGET
    assert budget.remaining == ii.DAILY_REQUEST_BUDGET


def test_budget_stops_at_limit():
    budget = ii.RequestBudget(2)
    assert budget.take() is True
    assert budget.take() is True
    assert budget.take() is False
    assert budget.used == 2
    assert budget.remaining == 0


def test_plan_skips_already_populated_records():
    plan = _plan()
    assert [p.player_id for p in plan.pending_players] == [1]
    assert [t.team_id for t in plan.pending_teams] == [2]
    assert len(plan.players) == 2
    assert len(plan.teams) == 2


def test_plan_is_deterministic():
    plan = ii.plan_targets(
        players=[
            ii.PlayerTarget(player_id=9, api_player_id="9", name="B", has_photo=False),
            ii.PlayerTarget(player_id=3, api_player_id="3", name="A", has_photo=False),
        ],
        teams=[],
    )
    assert [p.player_id for p in plan.players] == [3, 9]


def test_default_run_makes_no_external_requests(monkeypatch):
    async def fake_load(targets):
        return _plan()

    def explode(*args, **kwargs):
        raise AssertionError("external API call attempted")

    monkeypatch.setattr(ii, "load_targets", fake_load)
    monkeypatch.setattr(ii.ApiFootballProvider, "get_player_profile", explode)
    monkeypatch.setattr(ii.ApiFootballProvider, "get_team", explode)

    assert asyncio.run(ii.run([])) == 0


def test_apply_without_fetch_makes_no_external_requests(monkeypatch):
    async def fake_load(targets):
        return _plan()

    def explode(*args, **kwargs):
        raise AssertionError("external API call attempted")

    monkeypatch.setattr(ii, "load_targets", fake_load)
    monkeypatch.setattr(ii.ApiFootballProvider, "get_player_profile", explode)
    monkeypatch.setattr(ii.ApiFootballProvider, "get_team", explode)

    assert asyncio.run(ii.run(["--apply"])) == 0


def test_fetch_run_stores_photos_and_respects_budget(monkeypatch):
    async def fake_load(targets):
        return _plan()

    calls = []

    async def fake_profile(self, player_id):
        calls.append(player_id)
        return {"player": {"id": player_id, "name": "E. Haaland", "photo": "https://example.com/photo.png"}}

    stored = []

    async def fake_set_photo(player_id, photo_url):
        stored.append((player_id, photo_url))

    async def fake_set_crest(team_id, crest_url):
        stored.append((team_id, crest_url))

    monkeypatch.setattr(ii, "load_targets", fake_load)
    monkeypatch.setattr(ii.ApiFootballProvider, "get_player_profile", fake_profile)
    monkeypatch.setattr(ii, "_set_player_photo", fake_set_photo)
    monkeypatch.setattr(ii, "_set_team_crest", fake_set_crest)

    result = asyncio.run(ii.run(["--apply", "--fetch", "--max-requests", "1"]))

    assert result == 0
    assert calls == [1100]
    assert stored == [(1, "https://example.com/photo.png")]
