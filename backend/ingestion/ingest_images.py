"""Ingest image URLs (player photos, team crests) into the database.

Image references are fetched from API-Football during a controlled ingestion
run and stored in the canonical tables, so that rendering a page never calls
an external API.

Safety rules:
  * External API requests are opt-in (--fetch). A default invocation only
    builds a plan — it performs no requests and no writes.
  * Every run is capped by an API request budget. The daily quota is never
    assumed to be available; the run stops as soon as the budget is spent.
  * Existing image data is never overwritten: players that already have a
    photo and teams that already have a crest are skipped. Runs are therefore
    idempotent and resumable — an interrupted run continues where it stopped.
  * Only provider IDs that already exist in external_ids are used. No player
    or team mapping is guessed or constructed here.

Usage:
    cd backend && python -m ingestion.ingest_images
    cd backend && python -m ingestion.ingest_images --apply
    cd backend && python -m ingestion.ingest_images --apply --fetch --max-requests 25
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ingest_images")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from db.models.external_id import ExternalId  # noqa: E402
from db.models.player import Player  # noqa: E402
from db.models.image_ingestion_quota import ImageIngestionQuota  # noqa: E402
from db.models.team import Team  # noqa: E402
from db.session import async_session  # noqa: E402
from providers.api_football.client import (  # noqa: E402
    ApiFootballProvider,
    APIError,
    APIInvalidResponseError,
    APIRateLimitError,
)


PROVIDER = "api_football"

# API-Football free tier: 100 requests per day. A single run never plans to
# spend more than this, and the effective cap is the smaller of this value
# and --max-requests.
DAILY_REQUEST_BUDGET = 100
DEFAULT_MAX_REQUESTS = 25
DAILY_IMAGE_INGESTION_CAP = min(
    int(os.getenv("IMAGE_INGESTION_DAILY_CAP", str(DAILY_REQUEST_BUDGET))),
    DAILY_REQUEST_BUDGET,
)


# ─── Plan model ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlayerTarget:
    player_id: int
    api_player_id: str
    name: str
    has_photo: bool


@dataclass(frozen=True)
class TeamTarget:
    team_id: int
    api_team_id: str
    name: str
    has_crest: bool


@dataclass
class IngestPlan:
    players: list[PlayerTarget] = field(default_factory=list)
    teams: list[TeamTarget] = field(default_factory=list)

    @property
    def pending_players(self) -> list[PlayerTarget]:
        return [p for p in self.players if not p.has_photo]

    @property
    def pending_teams(self) -> list[TeamTarget]:
        return [t for t in self.teams if not t.has_crest]


def plan_targets(players: list[PlayerTarget], teams: list[TeamTarget]) -> IngestPlan:
    """Build a deterministic plan, splitting populated from pending records."""
    return IngestPlan(
        players=sorted(players, key=lambda p: p.player_id),
        teams=sorted(teams, key=lambda t: t.team_id),
    )


class RequestBudget:
    """Counts external API requests and refuses to exceed its limit."""

    def __init__(self, limit: int) -> None:
        if limit < 0:
            raise ValueError("limit must be >= 0")
        self.limit = min(limit, DAILY_REQUEST_BUDGET)
        self.used = 0

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    def take(self) -> bool:
        """Consume one request slot. False when the budget is exhausted."""
        if self.remaining <= 0:
            return False
        self.used += 1
        return True


class QuotaLedger:
    """Persistent, UTC-day-scoped quota ledger backed by the database."""

    def __init__(self, daily_cap: int) -> None:
        self.daily_cap = min(daily_cap, DAILY_REQUEST_BUDGET)

    @staticmethod
    def utc_today() -> date:
        return datetime.now(timezone.utc).date()

    async def reserve(self, session) -> bool:
        """Atomically reserve one slot for today. Returns False if cap reached."""
        from sqlalchemy import select
        today = self.utc_today()
        async with session.begin():
            row = (await session.execute(
                select(ImageIngestionQuota).where(ImageIngestionQuota.utc_date == today).with_for_update()
            )).scalar_one_or_none()
    async def reserve(self, session) -> bool:
        """Atomically reserve one slot for today. Returns False if cap reached."""
        from sqlalchemy import select
        today = self.utc_today()
        async with session.begin():
            row = (await session.execute(
                select(ImageIngestionQuota).where(ImageIngestionQuota.utc_date == today).with_for_update()
            )).scalar_one_or_none()
            if row is None:
                row = ImageIngestionQuota(utc_date=today, daily_cap=self.daily_cap, reserved=0, used=0)
                session.add(row)
                await session.flush()
            else:
                if row.daily_cap != self.daily_cap:
                    raise ValueError(
                        f"configured daily cap {self.daily_cap} conflicts with persisted cap {row.daily_cap}"
                    )
            if row.reserved + row.used >= row.daily_cap:
                return False
            row.reserved += 1
            row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return True

    async def reconcile(self, session, *, consumed: bool) -> None:
        """Move one reservation to used (if consumed) or release it."""
        from sqlalchemy import select
        today = self.utc_today()
        async with session.begin():
            row = (await session.execute(
                select(ImageIngestionQuota).where(ImageIngestionQuota.utc_date == today).with_for_update()
            )).scalar_one_or_none()
            if row is None:
                return
            if row.reserved > 0:
                row.reserved -= 1
            if consumed and row.used < row.daily_cap:
                row.used += 1
            row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)


# ─── CLI ───────────────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ingestion.ingest_images",
        description="Plan or run image URL ingestion (player photos, team crests).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Enable database writes. Without it the run is a plan only.",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Allow external API requests. Requires --apply.",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=DEFAULT_MAX_REQUESTS,
        help=(
            f"Maximum external API requests for this run "
            f"(default {DEFAULT_MAX_REQUESTS}, hard cap {DAILY_REQUEST_BUDGET})."
        ),
    )
    parser.add_argument(
        "--targets",
        choices=("players", "teams", "both"),
        default="both",
        help="Which entity types to process (default: both).",
    )
    args = parser.parse_args(argv)

    if args.fetch and not args.apply:
        parser.error("--fetch requires --apply: refusing to spend quota on a run that cannot store results")
    if args.max_requests < 0:
        parser.error("--max-requests must be >= 0")
    return args


# ─── Data access ──────────────────────────────────────────────────────────


async def load_targets(targets: str) -> IngestPlan:
    """Resolve ingestion targets from the existing provider-ID mappings."""
    players: list[PlayerTarget] = []
    teams: list[TeamTarget] = []

    async with async_session() as session:
        if targets in ("players", "both"):
            rows = (await session.execute(
                select(ExternalId, Player)
                .join(Player, Player.id == ExternalId.player_id)
                .where(
                    ExternalId.provider == PROVIDER,
                    ExternalId.entity_type == "player",
                )
            )).all()
            players = [
                PlayerTarget(
                    player_id=player.id,
                    api_player_id=ext.external_id,
                    name=player.name,
                    has_photo=bool(player.photo_url),
                )
                for ext, player in rows
            ]

        if targets in ("teams", "both"):
            rows = (await session.execute(
                select(ExternalId, Team)
                .join(Team, Team.id == ExternalId.team_id)
                .where(
                    ExternalId.provider == PROVIDER,
                    ExternalId.entity_type == "team",
                )
            )).all()
            teams = [
                TeamTarget(
                    team_id=team.id,
                    api_team_id=ext.external_id,
                    name=team.name,
                    has_crest=bool(team.crest_url),
                )
                for ext, team in rows
            ]

    return plan_targets(players, teams)


async def _set_player_photo(player_id: int, photo_url: str) -> None:
    """Store a player photo URL. Committed per record so runs stay resumable."""
    async with async_session() as session:
        player = await session.get(Player, player_id)
        if player is None:
            return
        if player.photo_url:
            return
        player.photo_url = photo_url
        player.photo_updated_at = datetime.utcnow()
        await session.commit()


async def _set_team_crest(team_id: int, crest_url: str) -> None:
    """Store a team crest URL. Existing crest data is never overwritten."""
    async with async_session() as session:
        team = await session.get(Team, team_id)
        if team is None:
            return
        if team.crest_url:
            return
        team.crest_url = crest_url
        await session.commit()


# ─── Run ───────────────────────────────────────────────────────────────────


@dataclass
class RunStats:
    players_updated: int = 0
    players_skipped: int = 0
    players_failed: int = 0
    teams_updated: int = 0
    teams_skipped: int = 0
    teams_failed: int = 0
    api_requests: int = 0
    aborted_reason: str | None = None


async def ingest_players(
    plan: IngestPlan,
    provider: ApiFootballProvider,
    budget: RequestBudget,
    ledger=None,
) -> RunStats:
    """Fetch and store player photos for players that do not have one yet."""
    stats = RunStats()
    for target in plan.pending_players:
        if not budget.take():
            stats.aborted_reason = "request budget exhausted"
            logger.warning(
                "Request budget exhausted after %d request(s); stopping. Re-run later to continue.",
                budget.used,
            )
            break
        if ledger is not None:
            try:
                async with async_session() as sess:
                    ok = await ledger.reserve(sess)
            except Exception as e:  # noqa: BLE001
                logger.error("Quota accounting unavailable; aborting: %s", e)
                stats.aborted_reason = "quota accounting unavailable"
                break
            if not ok:
                stats.aborted_reason = "daily quota exhausted"
                logger.warning("Daily image-ingestion quota exhausted; stopping.")
                break
        try:
            payload = await provider.get_player_profile(int(target.api_player_id))
        except APIRateLimitError:
            stats.aborted_reason = "upstream rate limit (HTTP 429)"
            logger.error("Upstream rate limit reached; stopping. Progress so far is stored.")
            if ledger is not None:
                try:
                    async with async_session() as sess:
                        await ledger.reconcile(sess, consumed=True)
                except Exception:  # noqa: BLE001
                    pass
            break
        except APIInvalidResponseError as e:
            stats.aborted_reason = f"upstream rejected the request: {e}"
            logger.error("Upstream rejected the request (%s); stopping.", e)
            if ledger is not None:
                try:
                    async with async_session() as sess:
                        await ledger.reconcile(sess, consumed=True)
                except Exception:  # noqa: BLE001
                    pass
            break
        except APIError as e:
            stats.players_failed += 1
            logger.warning("Player %s (api id %s) failed: %s", target.name, target.api_player_id, e)
            if ledger is not None:
                try:
                    async with async_session() as sess:
                        await ledger.reconcile(sess, consumed=True)
                except Exception:  # noqa: BLE001
                    pass
            continue

        photo = ((payload or {}).get("player") or {}).get("photo")
        if not photo:
            stats.players_skipped += 1
            logger.info("Player %s has no photo URL upstream", target.name)
            if ledger is not None:
                try:
                    async with async_session() as sess:
                        await ledger.reconcile(sess, consumed=True)
                except Exception:  # noqa: BLE001
                    pass
            continue

        await _set_player_photo(target.player_id, photo)
        stats.players_updated += 1
        logger.info("Stored photo for player %s (id %s)", target.name, target.player_id)
        if ledger is not None:
            try:
                async with async_session() as sess:
                    await ledger.reconcile(sess, consumed=True)
            except Exception:  # noqa: BLE001
                pass
    return stats


async def ingest_teams(
    plan: IngestPlan,
    provider: ApiFootballProvider,
    budget: RequestBudget,
    ledger=None,
) -> RunStats:
    """Fetch and store team crests for teams that do not have one yet."""
    stats = RunStats()
    for target in plan.pending_teams:
        if not budget.take():
            stats.aborted_reason = "request budget exhausted"
            logger.warning(
                "Request budget exhausted after %d request(s); stopping. Re-run later to continue.",
                budget.used,
            )
            break
        if ledger is not None:
            try:
                async with async_session() as sess:
                    ok = await ledger.reserve(sess)
            except Exception as e:  # noqa: BLE001
                logger.error("Quota accounting unavailable; aborting: %s", e)
                stats.aborted_reason = "quota accounting unavailable"
                break
            if not ok:
                stats.aborted_reason = "daily quota exhausted"
                logger.warning("Daily image-ingestion quota exhausted; stopping.")
                break
        try:
            payload = await provider.get_team(int(target.api_team_id))
        except APIRateLimitError:
            stats.aborted_reason = "upstream rate limit (HTTP 429)"
            logger.error("Upstream rate limit reached; stopping. Progress so far is stored.")
            if ledger is not None:
                try:
                    async with async_session() as sess:
                        await ledger.reconcile(sess, consumed=True)
                except Exception:  # noqa: BLE001
                    pass
            break
        except APIInvalidResponseError as e:
            stats.aborted_reason = f"upstream rejected the request: {e}"
            logger.error("Upstream rejected the request (%s); stopping.", e)
            if ledger is not None:
                try:
                    async with async_session() as sess:
                        await ledger.reconcile(sess, consumed=True)
                except Exception:  # noqa: BLE001
                    pass
            break
        except APIError as e:
            stats.teams_failed += 1
            logger.warning("Team %s (api id %s) failed: %s", target.name, target.api_team_id, e)
            if ledger is not None:
                try:
                    async with async_session() as sess:
                        await ledger.reconcile(sess, consumed=True)
                except Exception:  # noqa: BLE001
                    pass
            continue

        logo = ((payload or {}).get("team") or {}).get("logo")
        if not logo:
            stats.teams_skipped += 1
            logger.info("Team %s has no logo URL upstream", target.name)
            if ledger is not None:
                try:
                    async with async_session() as sess:
                        await ledger.reconcile(sess, consumed=True)
                except Exception:  # noqa: BLE001
                    pass
            continue

        await _set_team_crest(target.team_id, logo)
        stats.teams_updated += 1
        logger.info("Stored crest for team %s (id %s)", target.name, target.team_id)
        if ledger is not None:
            try:
                async with async_session() as sess:
                    await ledger.reconcile(sess, consumed=True)
            except Exception:  # noqa: BLE001
                pass
    return stats


async def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        plan = await load_targets(args.targets)
    except SQLAlchemyError as e:
        logger.error(
            "Could not read the ingestion plan: %s. If players.photo_url is missing, "
            "apply the migration first: alembic -c db/alembic.ini upgrade head",
            e,
        )
        return 1

    pending_players = plan.pending_players
    pending_teams = plan.pending_teams
    logger.info(
        "Plan: %d player(s) pending a photo, %d team(s) pending a crest "
        "(%d player(s) and %d team(s) already populated)",
        len(pending_players),
        len(pending_teams),
        len(plan.players) - len(pending_players),
        len(plan.teams) - len(pending_teams),
    )
    for target in pending_players:
        logger.info("  player  id=%-5s api_id=%-8s %s", target.player_id, target.api_player_id, target.name)
    for target in pending_teams:
        logger.info("  team    id=%-5s api_id=%-8s %s", target.team_id, target.api_team_id, target.name)

    if not args.apply:
        logger.info(
            "Plan only — no database writes and no external API requests. "
            "Re-run with --apply to store results, and --apply --fetch to contact API-Football."
        )
        return 0

    if not args.fetch:
        logger.info(
            "--apply without --fetch: image URLs come from API-Football, so no requests are made "
            "and nothing is written. Re-run with --apply --fetch to fetch."
        )
        return 0

    budget = RequestBudget(args.max_requests)
    ledger = QuotaLedger(DAILY_IMAGE_INGESTION_CAP)
    provider = ApiFootballProvider()
    stats = RunStats()

    if args.targets in ("players", "both"):
        player_stats = await ingest_players(plan, provider, budget, ledger)
        stats.players_updated = player_stats.players_updated
        stats.players_skipped = player_stats.players_skipped
        stats.players_failed = player_stats.players_failed
        if player_stats.aborted_reason:
            stats.aborted_reason = player_stats.aborted_reason

    if args.targets in ("teams", "both") and not stats.aborted_reason:
        team_stats = await ingest_teams(plan, provider, budget, ledger)
        stats.teams_updated = team_stats.teams_updated
        stats.teams_skipped = team_stats.teams_skipped
        stats.teams_failed = team_stats.teams_failed
        if team_stats.aborted_reason:
            stats.aborted_reason = team_stats.aborted_reason

    stats.api_requests = budget.used
    logger.info(
        "Summary: players updated=%d skipped=%d failed=%d | teams updated=%d skipped=%d failed=%d | "
        "api_requests=%d (budget %d)",
        stats.players_updated,
        stats.players_skipped,
        stats.players_failed,
        stats.teams_updated,
        stats.teams_skipped,
        stats.teams_failed,
        stats.api_requests,
        budget.limit,
    )
    if stats.aborted_reason:
        logger.warning("Run stopped early: %s", stats.aborted_reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
