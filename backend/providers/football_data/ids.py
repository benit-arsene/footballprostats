"""External ID extraction for football-data.org provider."""

from typing import Any


def extract_team_external_ids(api_team: dict) -> list[tuple[str, str]]:
    """Extract external IDs from football-data.org team response."""
    results: list[tuple[str, str]] = []
    if api_team and "id" in api_team:
        results.append(("football_data", str(api_team["id"])))
    return results


def extract_player_external_ids(api_player: dict) -> list[tuple[str, str]]:
    """Extract external IDs from football-data.org player response."""
    results: list[tuple[str, str]] = []
    if api_player and "id" in api_player:
        results.append(("football_data", str(api_player["id"])))
    return results


def extract_match_external_ids(api_match: dict) -> list[tuple[str, str]]:
    """Extract external IDs from football-data.org match response."""
    results: list[tuple[str, str]] = []
    if api_match and "id" in api_match:
        results.append(("football_data", str(api_match["id"])))
    return results


def competition_code(api_comp: dict | None) -> str | None:
    """The provider's own competition code from a competition payload.

    football-data.org fixtures are requested by competition code (``PL``,
    ``PD``, …), not by the numeric id. The code is the canonical identifier we
    store in ``external_ids``; a payload without a code yields ``None`` rather
    than a numeric id that the fixtures contract cannot use.
    """
    if not isinstance(api_comp, dict):
        return None
    code = api_comp.get("code")
    if not isinstance(code, str):
        return None
    code = code.strip().upper()
    return code or None


def canonical_competition_code(value: str | int) -> str:
    """Validate and normalise a football-data.org competition code.

    Only codes the provider's fixtures contract supports are accepted. Numeric
    values (the provider's own numeric id, or another provider's league id such
    as API-Football's ``39``) are rejected so id spaces can never be confused.
    """
    from providers.football_data.adapters import CODE_TO_COMPETITION_ID

    code = str(value if value is not None else "").strip().upper()
    if code not in CODE_TO_COMPETITION_ID:
        raise ValueError(
            f"{value!r} is not a supported football-data.org competition code "
            f"(expected one of {sorted(CODE_TO_COMPETITION_ID)})"
        )
    return code


def extract_competition_external_ids(api_comp: dict | None) -> list[tuple[str, str]]:
    """External ID for a football-data.org competition: its competition code."""
    code = competition_code(api_comp)
    return [("football_data", code)] if code else []
