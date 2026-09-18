"""Normalization: events."""

from models import MatchEvent, EventType


def normalize_event_type(api_type: str, api_detail: str | None) -> EventType:
    """Normalize an API-Football event type string to canonical EventType."""
    mapping = {
        "Goal": {None: "goal", "Own Goal": "own_goal", "Penalty": "penalty_scored"},
        "Card": {
            "Yellow Card": "yellow_card",
            "Red Card": "red_card",
            "Second Yellow card": "second_yellow_card",
        },
        "Var": {"": "var_decision"},
        "subst": {"": "substitution"},
        "Penalty": {None: "penalty_scored", "Missed Penalty": "penalty_missed"},
    }
    return mapping.get(api_type, {}).get(api_detail, "goal")
