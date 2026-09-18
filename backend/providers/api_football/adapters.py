"""API-Football adapters — raw JSON → canonical Pydantic models.

This module maps API-Football response structures to canonical
models defined in models.py. This is the adapter layer of the
provider — the raw provider JSON never leaks outside this package.
"""

from models import (
    MatchSummary,
    MatchDetail,
    MatchStatus,
    EventType,
    TeamSummary,
    PlayerSummary,
    LeagueSummary,
    MatchEvent,
    MatchStats,
    LineupPlayer,
    StandingRow,
    TopScorer,
    TeamProfile,
)


def _status_map(api_status: str, elapsed: int | None) -> MatchStatus:
    mapping = {
        "NS": "scheduled", "TBD": "scheduled",
        "1H": "live", "HT": "live", "2H": "live",
        "ET": "live", "P": "live", "BT": "live", "LIVE": "live",
        "FT": "finished", "PST": "postponed", "CANC": "cancelled",
        "AWD": "finished", "WO": "finished",
    }
    return mapping.get(api_status, "scheduled")


def _event_type_map(api_type: str, api_detail: str | None) -> EventType:
    if api_type == "Goal":
        if api_detail == "Own Goal":
            return "own_goal"
        if api_detail == "Penalty":
            return "penalty_scored"
        return "goal"
    if api_type == "Card":
        if api_detail == "Yellow Card":
            return "yellow_card"
        if api_detail == "Red Card":
            return "red_card"
        if api_detail == "Second Yellow card":
            return "second_yellow_card"
        return "yellow_card"
    if api_type == "Var":
        return "var_decision"
    if api_type == "subst":
        return "substitution"
    if api_type == "Penalty":
        if api_detail == "Missed Penalty":
            return "penalty_missed"
        return "penalty_scored"
    return "goal"


def _make_slug(name: str, id: int) -> str:
    import re
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return f"{slug}-{id}"


_LEAGUE_NAMES = {
    39: ("Premier League", "England"),
    140: ("La Liga", "Spain"),
    2: ("Champions League", "Europe"),
    78: ("Bundesliga", "Germany"),
    135: ("Serie A", "Italy"),
    61: ("Ligue 1", "France"),
}


def _league_id_to_name(league_id: int) -> tuple[str, str]:
    name, country = _LEAGUE_NAMES.get(league_id, ("Unknown League", "Unknown"))
    return name, country


class ApiFootballAdapters:
    """Adapter methods for API-Football responses → canonical models."""

    @staticmethod
    def team_summary(api_team: dict) -> TeamSummary:
        return TeamSummary(
            id=api_team["id"],
            name=api_team["name"],
            slug=_make_slug(api_team["name"], api_team["id"]),
            crest_url=api_team.get("logo") or "",
        )

    @staticmethod
    def league_summary(api_league: dict, api_country: dict | None = None) -> LeagueSummary:
        country = api_country.get("name", "") if api_country else ""
        league_id = api_league["id"]
        name = api_league.get("name", f"League {league_id}")
        return LeagueSummary(
            id=league_id,
            name=name,
            slug=_make_slug(name, league_id),
            country=country,
            logo_url=api_league.get("logo", ""),
        )

    @staticmethod
    def player_summary(api_player: dict) -> PlayerSummary:
        return PlayerSummary(
            id=api_player["id"],
            name=api_player["name"],
            slug=_make_slug(api_player["name"], api_player["id"]),
            position=api_player.get("position") or "",
            number=api_player.get("number"),
            nationality=api_player.get("nationality") or "",
        )

    @staticmethod
    def match_summary(fixture: dict) -> MatchSummary:
        goals = fixture.get("goals", {})
        teams = fixture.get("teams", {})
        league = fixture.get("league", {})
        fixture_info = fixture.get("fixture", {})
        status = fixture_info.get("status", {})

        home = teams.get("home", {})
        away = teams.get("away", {})
        fixture_id = fixture_info.get("id", 0)

        league_summary = ApiFootballAdapters.league_summary(league)

        return MatchSummary(
            id=fixture_id,
            slug=_make_slug(f"{home.get('name', '')} vs {away.get('name', '')}", fixture_id),
            status=_status_map(status.get("short", "NS"), status.get("elapsed")),
            minute=status.get("elapsed"),
            date=fixture_info.get("date", "")[:10],
            kickoff_time=fixture_info.get("date", "")[11:16],
            venue=fixture_info.get("venue", {}).get("name", ""),
            league=league_summary,
            home_team=ApiFootballAdapters.team_summary(home) if home.get("id") else TeamSummary(
                id=0, name="TBD", slug="tbd-0", crest_url=""
            ),
            away_team=ApiFootballAdapters.team_summary(away) if away.get("id") else TeamSummary(
                id=0, name="TBD", slug="tbd-0", crest_url=""
            ),
            home_score=goals.get("home") or 0,
            away_score=goals.get("away") or 0,
        )

    @staticmethod
    def match_detail(fixture: dict) -> MatchDetail:
        summary = ApiFootballAdapters.match_summary(fixture)
        fixture_info = fixture.get("fixture", {})

        events = []
        for i, ev in enumerate(fixture.get("events", []) or []):
            team_data = ev.get("team", {})
            player_data = ev.get("player", {})
            assist_data = ev.get("assist", {}) or {}

            ev_team = TeamSummary(
                id=team_data.get("id", 0),
                name=team_data.get("name") or "",
                slug=_make_slug(team_data.get("name") or "", team_data.get("id", 0)),
                crest_url=team_data.get("logo") or "",
            )

            ev_player = PlayerSummary(
                id=player_data.get("id") or 0,
                name=player_data.get("name") or "Unknown",
                slug=_make_slug(player_data.get("name", ""), player_data.get("id") or 0),
                position="", number=None, nationality="",
            )

            ev_assist = None
            if assist_data.get("id"):
                ev_assist = PlayerSummary(
                    id=assist_data["id"] or 0,
                    name=assist_data.get("name", "Unknown"),
                    slug=_make_slug(assist_data.get("name", ""), assist_data["id"]),
                    position="", number=None, nationality="",
                )

            events.append(MatchEvent(
                id=i + 1,
                minute=ev.get("time", {}).get("elapsed", 0),
                added_time=ev.get("time", {}).get("extra"),
                type=_event_type_map(ev.get("type", ""), ev.get("detail", "")),
                team=ev_team,
                player=ev_player,
                second_player=ev_assist,
                detail=ev.get("comments"),
            ))

        home_lineup = []
        away_lineup = []
        for lineup in fixture.get("lineups", []) or []:
            team_info = lineup.get("team", {})
            is_home = team_info.get("id") == fixture.get("teams", {}).get("home", {}).get("id")
            for player in lineup.get("startXI", []) or []:
                p = player.get("player", {})
                lineup_player = LineupPlayer(
                    player=PlayerSummary(
                        id=p.get("id", 0), name=p.get("name", "Unknown"),
                        slug=_make_slug(p.get("name", ""), p.get("id", 0)),
                        position=p.get("pos") or "", number=p.get("number"),
                        nationality=p.get("nationality") or "",
                    ),
                    position=p.get("pos") or "",
                    shirt_number=p.get("number"),
                    rating=None,
                )
                if is_home:
                    home_lineup.append(lineup_player)
                else:
                    away_lineup.append(lineup_player)

        stats = None
        stats_list = fixture.get("statistics", [])
        if stats_list:
            home_stats = {}
            away_stats = {}
            for s in stats_list:
                team_id = s.get("team", {}).get("id")
                for stat in s.get("statistics", []):
                    type_name = stat.get("type", "")
                    value = stat.get("value")
                    if isinstance(value, str) and value.endswith("%"):
                        value = int(value.replace("%", ""))
                    elif isinstance(value, str):
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            value = 0
                    elif value is None:
                        value = 0
                    if team_id == fixture.get("teams", {}).get("home", {}).get("id"):
                        home_stats[type_name] = value
                    else:
                        away_stats[type_name] = value

            def _get_stat(name: str) -> tuple[int, int]:
                return (home_stats.get(name, 0), away_stats.get(name, 0))

            stats = MatchStats(
                possession=_get_stat("Ball Possession"),
                shots=_get_stat("Total Shots"),
                shots_on_target=_get_stat("Shots on Goal"),
                corners=_get_stat("Corner Kicks"),
                fouls=_get_stat("Fouls"),
                yellow_cards=_get_stat("Yellow Cards"),
                red_cards=_get_stat("Red Cards"),
            )

        referee = fixture_info.get("referee") or ""
        if isinstance(referee, str) and len(referee) > 50:
            referee = referee[:50]

        return MatchDetail(
            **summary.model_dump(),
            attendance=None,
            referee=referee,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            events=events,
            stats=stats,
        )

    @staticmethod
    def standing_row(api_row: dict) -> StandingRow:
        team = api_row.get("team", {})
        api_all = api_row.get("all", {})
        api_diff = api_row.get("goalsDiff", 0)
        form = api_row.get("form", "") or ""
        form_list = [f.strip() for f in form.split(",") if f.strip()] if form else []

        return StandingRow(
            position=api_row.get("rank", 0),
            team=ApiFootballAdapters.team_summary(team),
            played=api_all.get("played", 0),
            won=api_all.get("win", 0),
            drawn=api_all.get("draw", 0),
            lost=api_all.get("lose", 0),
            gf=api_all.get("goals", {}).get("for", 0) if isinstance(api_all.get("goals"), dict) else 0,
            ga=api_all.get("goals", {}).get("against", 0) if isinstance(api_all.get("goals"), dict) else 0,
            gd=api_diff,
            points=api_row.get("points", 0),
            form=form_list[-5:] if form_list else [],
        )

    @staticmethod
    def top_scorer(api_player: dict) -> TopScorer:
        player = api_player.get("player", {})
        team = api_player.get("statistics", [{}])[0].get("team", {}) if api_player.get("statistics") else {}
        stats = api_player.get("statistics", [{}])[0] if api_player.get("statistics") else {}

        return TopScorer(
            player=ApiFootballAdapters.player_summary(player),
            team=ApiFootballAdapters.team_summary(team) if team.get("id") else TeamSummary(
                id=0, name="Unknown", slug="unknown-0", crest_url=""
            ),
            goals=stats.get("goals", {}).get("total", 0) if isinstance(stats.get("goals"), dict) else 0,
            assists=stats.get("goals", {}).get("assists", 0) if isinstance(stats.get("goals"), dict) else 0,
        )
