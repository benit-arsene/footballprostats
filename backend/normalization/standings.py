"""Normalization: standings."""

from models import StandingRow


def normalize_standings(rows: list[dict]) -> list[StandingRow]:
    """Normalize a list of standing row dicts into canonical StandingRows."""
    from providers.api_football.adapters import ApiFootballAdapters
    return [ApiFootballAdapters.standing_row(row) for row in rows]
