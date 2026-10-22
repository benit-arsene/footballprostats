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


# ─── CORS ─────────────────────────────────────────────────────────────────

# Origins allowed to call the API. The Next.js dev server is reachable on
# both localhost and 127.0.0.1, and the browser sends the origin it was
# opened with.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
