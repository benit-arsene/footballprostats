"""
Player-related API endpoints.

Endpoints:
  GET /api/v1/players/{player_id} — player profile and career stats
"""

from fastapi import APIRouter, HTTPException

from models import PlayerProfile, TeamSummary, CareerStats, MatchLogEntry
from services import football_api
from services.mapper import map_player_summary, make_slug
from config import get_season_year

router = APIRouter(prefix="/api/v1/players", tags=["players"])


@router.get("/{player_id}", response_model=PlayerProfile)
async def get_player_profile(player_id: int):
    """
    Returns individual player career stats and match-by-match logs.
    """
    try:
        season = get_season_year()
        player_data = await football_api.get_player(player_id, season)
        if not player_data:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "NOT_FOUND", "message": f"Player {player_id} not found"}},
            )

        player_info = player_data.get("player", {})
        stats_list = player_data.get("statistics", [])

        # Get current team and stats
        current_stats = stats_list[0] if stats_list else {}
        team = current_stats.get("team", {})
        stats = current_stats.get("statistics", {})

        team_summary = map_team_summary(team) if team.get("id") else TeamSummary(
            id=0, name="Unknown", slug="unknown-0", crest_url=""
        )

        # Build career stats
        career = CareerStats(
            appearances=stats.get("games", {}).get("appearences", 0) if isinstance(stats.get("games"), dict) else 0,
            goals=stats.get("goals", {}).get("total", 0) if isinstance(stats.get("goals"), dict) else 0,
            assists=stats.get("goals", {}).get("assists", 0) if isinstance(stats.get("goals"), dict) else 0,
            yellow_cards=stats.get("cards", {}).get("yellow", 0) if isinstance(stats.get("cards"), dict) else 0,
            red_cards=stats.get("cards", {}).get("red", 0) if isinstance(stats.get("cards"), dict) else 0,
            minutes_played=stats.get("games", {}).get("minutes", 0) if isinstance(stats.get("games"), dict) else 0,
        )

        # Build match logs from fixtures
        match_logs = []
        try:
            fixtures = await football_api.get_fixtures_by_team(
                team.get("id", 0), season
            )
            for fixture in fixtures[:20]:  # last 20 matches
                f_teams = fixture.get("teams", {})
                f_goals = fixture.get("goals", {})
                f_fixture = fixture.get("fixture", {})
                home = f_teams.get("home", {})
                away = f_teams.get("away", {})

                # Determine opponent and result
                if home.get("id") == team.get("id"):
                    opponent = away.get("name", "TBD")
                    goals_for = f_goals.get("home", 0) or 0
                    goals_against = f_goals.get("away", 0) or 0
                else:
                    opponent = home.get("name", "TBD")
                    goals_for = f_goals.get("away", 0) or 0
                    goals_against = f_goals.get("home", 0) or 0

                if goals_for > goals_against:
                    result = "W"
                elif goals_for < goals_against:
                    result = "L"
                else:
                    result = "D"

                match_logs.append(MatchLogEntry(
                    match_id=f_fixture.get("id", 0),
                    match_slug=f"{opponent.lower().replace(' ', '-')}-{f_fixture.get('id', 0)}",
                    date=f_fixture.get("date", "")[:10],
                    opponent=opponent,
                    result=f"{result} {goals_for}-{goals_against}",
                    goals=0,  # Would need player-specific event data
                    assists=0,
                    rating=None,
                ))
        except Exception:
            pass

        # Player info
        dob = player_info.get("birth", {}).get("date", "")[:10]
        height = None
        if player_info.get("height"):
            try:
                height = int(player_info["height"].replace("cm", "").strip())
            except (ValueError, TypeError):
                pass

        return PlayerProfile(
            id=player_info["id"],
            name=player_info.get("name", ""),
            slug=make_slug(player_info.get("name", ""), player_info["id"]),
            position=current_stats.get("games", {}).get("position", "")
            if isinstance(current_stats.get("games"), dict) else "",
            number=current_stats.get("games", {}).get("number"),
            nationality=player_info.get("nationality", ""),
            date_of_birth=dob,
            height_cm=height,
            foot="",  # Not available in free tier
            team=team_summary,
            career_stats=career,
            match_logs=match_logs,
        )
    except HTTPException:
        raise
    except football_api.APIRateLimitError as e:
        raise HTTPException(status_code=429, detail={"error": {"code": "UPSTREAM_RATE_LIMITED", "message": str(e)}})
    except football_api.APIError as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "UPSTREAM_ERROR", "message": str(e)}})
