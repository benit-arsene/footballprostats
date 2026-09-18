"""Shared test fixtures and data."""

import pytest
from typing import Any

# ─── API-Football mock responses ───────────────────────────────

MOCK_FIXTURE_DETAIL: dict[str, Any] = {
    "response": [
        {
            "fixture": {
                "id": 101,
                "date": "2026-08-22T15:00:00Z",
                "timestamp": 1724317200,
                "status": {
                    "long": "1st Half",
                    "short": "1H",
                    "elapsed": 23,
                },
                "venue": {"id": 1, "name": "Emirates Stadium", "city": "London"},
                "referee": "Michael Oliver",
            },
            "league": {
                "id": 39,
                "name": "Premier League",
                "logo": "https://example.com/pl.png",
                "country": {"name": "England", "code": "GB", "flag": "https://flagcdn.com/w40/gb.png"},
            },
            "teams": {
                "home": {
                    "id": 42,
                    "name": "Arsenal",
                    "logo": "https://example.com/arsenal.png",
                },
                "away": {
                    "id": 43,
                    "name": "Chelsea",
                    "logo": "https://example.com/chelsea.png",
                },
            },
            "goals": {"home": 2, "away": 1},
            "events": [],
            "lineups": [],
            "statistics": [],
        }
    ]
}

MOCK_STANDINGS_RESPONSE: dict[str, Any] = {
    "response": [
        {
            "league": {
                "id": 39,
                "name": "Premier League",
                "logo": "https://example.com/pl.png",
            },
            "standings": [
                [
                    {
                        "rank": 1,
                        "team": {"id": 42, "name": "Arsenal", "logo": ""},
                        "all": {
                            "played": 28, "win": 22, "draw": 4, "lose": 2,
                            "goals": {"for": 68, "against": 24},
                        },
                        "goalsDiff": 44,
                        "points": 70,
                        "form": "W,W,D,W,W",
                    }
                ]
            ],
        }
    ]
}

MOCK_TEAM_RESPONSE: dict[str, Any] = {
    "response": [
        {
            "team": {
                "id": 42,
                "name": "Arsenal",
                "short_name": "ARS",
                "logo": "https://example.com/arsenal.png",
                "founded": 1886,
                "venue": {"name": "Emirates Stadium"},
                "league": {"id": 39, "name": "Premier League"},
            }
        }
    ]
}

MOCK_PLAYER_RESPONSE: dict[str, Any] = {
    "response": [
        {
            "player": {
                "id": 1854,
                "name": "Bukayo Saka",
                "position": "Attack",
                "number": 7,
                "nationality": "England",
                "birth": {"date": "2001-09-05"},
                "height": "178cm",
            },
            "statistics": [
                {
                    "games": {
                        "position": "RW",
                        "appearences": 28,
                        "minutes": 2420,
                        "number": 7,
                    },
                    "goals": {"total": 16, "assists": 8},
                    "cards": {"yellow": 3, "red": 0},
                    "team": {
                        "id": 42,
                        "name": "Arsenal",
                        "logo": "",
                    },
                }
            ],
        }
    ]
}
