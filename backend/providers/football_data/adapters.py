"""football-data.org adapters — raw JSON → canonical Pydantic models."""

from models import (
    LeagueSummary,
    TeamSummary,
    PlayerSummary,
    MatchSummary,
    MatchStatus,
    StandingRow,
)
from providers.api_football.adapters import _make_slug

# Mapping from internal competition IDs to football-data.org competition codes.
COMPETITION_CODE_MAP: dict[int, str] = {
    39: "PL",    # Premier League
    140: "PD",   # La Liga
    78: "BL1",   # Bundesliga
    135: "SA",   # Serie A
    61: "FL1",   # Ligue 1
    2: "CL",     # Champions League
}

# Reverse mapping
CODE_TO_COMPETITION_ID: dict[str, int] = {v: k for k, v in COMPETITION_CODE_MAP.items()}


def _status_map(api_status: str) -> MatchStatus:
    mapping = {
        "SCHEDULED": "scheduled",
        "TIMED": "scheduled",
        "IN_PLAY": "live",
        "PAUSED": "live",
        "FINISHED": "finished",
        "POSTPONED": "postponed",
        "SUSPENDED": "postponed",
        "CANCELLED": "cancelled",
    }
    return mapping.get(api_status, "scheduled")


class FootballDataAdapters:
    """Adapter methods for football-data.org responses → canonical models."""

    @staticmethod
    def competition_summary(api_comp: dict) -> LeagueSummary:
        comp_id = api_comp.get("id", 0)
        # Map back to internal ID if known
        internal_id = CODE_TO_COMPETITION_ID.get(api_comp.get("code", ""), comp_id)
        name = api_comp.get("name", f"Competition {comp_id}")
        return LeagueSummary(
            id=internal_id,
            name=name,
            slug=_make_slug(name, internal_id),
            country=api_comp.get("area", {}).get("name", ""),
            logo_url=api_comp.get("emblem", ""),
        )

    @staticmethod
    def team_summary(api_team: dict) -> TeamSummary:
        team_id = api_team.get("id", 0)
        name = api_team.get("name", f"Team {team_id}")
        return TeamSummary(
            id=team_id,
            name=name,
            slug=_make_slug(name, team_id),
            crest_url=api_team.get("crest", ""),
        )

    @staticmethod
    def match_summary(api_match: dict) -> MatchSummary:
        from models import LeagueSummary, TeamSummary

        fixture_id = api_match.get("id", 0)
        home = api_match.get("homeTeam", {}) or {}
        away = api_match.get("awayTeam", {}) or {}
        comp = api_match.get("competition", {}) or {}
        score = api_match.get("score", {}) or {}
        full_time = score.get("fullTime", {}) or {}

        comp_id = comp.get("id", 0)
        internal_comp_id = CODE_TO_COMPETITION_ID.get(comp.get("code", ""), comp_id)
        comp_name = comp.get("name", "Unknown")

        league_summary = LeagueSummary(
            id=internal_comp_id,
            name=comp_name,
            slug=_make_slug(comp_name, internal_comp_id),
            country=comp.get("area", {}).get("name", "") if isinstance(comp.get("area"), dict) else "",
            logo_url=comp.get("emblem", ""),
        )

        home_team = TeamSummary(
            id=home.get("id", 0),
            name=home.get("name", "TBD"),
            slug=_make_slug(home.get("name", "tbd"), home.get("id", 0)),
            crest_url=home.get("crest", ""),
        )
        away_team = TeamSummary(
            id=away.get("id", 0),
            name=away.get("name", "TBD"),
            slug=_make_slug(away.get("name", "tbd"), away.get("id", 0)),
            crest_url=away.get("crest", ""),
        )

        utc_date = api_match.get("utcDate", "")
        date_str = utc_date[:10] if utc_date else ""
        kickoff = utc_date[11:16] if len(utc_date) >= 16 else ""

        return MatchSummary(
            id=fixture_id,
            slug=_make_slug(f"{home.get('name', '')} vs {away.get('name', '')}", fixture_id),
            status=_status_map(api_match.get("status", "SCHEDULED")),
            minute=None,
            date=date_str,
            kickoff_time=kickoff,
            venue=api_match.get("venue", "") or "",
            league=league_summary,
            home_team=home_team,
            away_team=away_team,
            home_score=full_time.get("home") or 0,
            away_score=full_time.get("away") or 0,
        )

    @staticmethod
    def standing_row(api_row: dict) -> StandingRow:
        team = api_row.get("team", {}) or {}
        return StandingRow(
            position=api_row.get("position", 0),
            team=FootballDataAdapters.team_summary(team),
            played=api_row.get("playedGames", 0),
            won=api_row.get("won", 0),
            drawn=api_row.get("draw", 0),
            lost=api_row.get("lost", 0),
            gf=api_row.get("goalsFor", 0),
            ga=api_row.get("goalsAgainst", 0),
            gd=api_row.get("goalDifference", 0),
            points=api_row.get("points", 0),
            form=[c for c in (api_row.get("form") or "") if c in "WDLD"],
        )