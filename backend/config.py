import os

# ─── API-Football Connection ──────────────────────────────────────────────

API_KEY = os.getenv("APIFOOTBALL_KEY", "")
API_HOST = os.getenv("APIFOOTBALL_HOST", "v3.football.api-sports.io")
BASE_URL = f"https://{API_HOST}"
REQUEST_TIMEOUT = 10.0

# ─── League IDs ────────────────────────────────────────────────────────────

LEAGUE_IDS = {
    "premier_league": 39,
    "la_liga": 140,
    "champions_league": 2,
    "bundesliga": 78,
    "serie_a": 135,
}

# Leagues featured on the homepage match list and live summary.
HOME_LEAGUE_IDS = {39, 140}  # Premier League, La Liga only

# ─── Season ────────────────────────────────────────────────────────────────


def get_season_year() -> int:
    from datetime import datetime

    now = datetime.now()
    if now.month >= 8:
        return now.year
    return now.year - 1
