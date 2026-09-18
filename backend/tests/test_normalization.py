"""Tests for normalization pipeline."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import MOCK_FIXTURE_DETAIL, MOCK_STANDINGS_RESPONSE
from normalization.matches import normalize_match_summary, normalize_match_detail
from normalization.standings import normalize_standings
from normalization.teams import normalize_team_summary
from normalization.events import normalize_event_type
from models import MatchSummary, MatchDetail, StandingRow


class TestNormalizationMatches:
    def test_normalize_match_summary(self):
        data = MOCK_FIXTURE_DETAIL["response"][0]
        result = normalize_match_summary(data)
        assert isinstance(result, MatchSummary)
        assert result.id == 101
        assert result.home_score == 2

    def test_normalize_match_detail(self):
        data = MOCK_FIXTURE_DETAIL["response"][0]
        result = normalize_match_detail(data)
        assert isinstance(result, MatchDetail)
        assert result.referee == "Michael Oliver"

    def test_normalize_standings(self):
        rows = MOCK_STANDINGS_RESPONSE["response"][0]["standings"][0]
        results = normalize_standings(rows)
        assert len(results) == 1
        assert isinstance(results[0], StandingRow)
        assert results[0].position == 1
        assert results[0].team.name == "Arsenal"


class TestNormalizationEvents:
    def test_goal_normalization(self):
        assert normalize_event_type("Goal", None) == "goal"
        assert normalize_event_type("Goal", "Normal Goal") == "goal"
        assert normalize_event_type("Goal", "Own Goal") == "own_goal"
        assert normalize_event_type("Goal", "Penalty") == "penalty_scored"

    def test_card_normalization(self):
        assert normalize_event_type("Card", "Yellow Card") == "yellow_card"
        assert normalize_event_type("Card", "Red Card") == "red_card"
        assert normalize_event_type("Card", "Second Yellow card") == "second_yellow_card"

    def test_var_normalization(self):
        assert normalize_event_type("Var", "") == "var_decision"

    def test_substitution_normalization(self):
        assert normalize_event_type("subst", "") == "substitution"

    def test_penalty_normalization(self):
        assert normalize_event_type("Penalty", None) == "penalty_scored"
        assert normalize_event_type("Penalty", "Missed Penalty") == "penalty_missed"

    def test_fallback_is_goal(self):
        assert normalize_event_type("Unknown", "Unknown Detail") == "goal"


class TestNormalizationTeams:
    def test_normalize_team_summary(self):
        from conftest import MOCK_TEAM_RESPONSE
        data = MOCK_TEAM_RESPONSE["response"][0]["team"]
        result = normalize_team_summary(data)
        assert result.name == "Arsenal"
        assert result.id == 42


class TestProviderSelectionConfig:
    def test_config_has_all_entity_types(self):
        from providers.config import PROVIDER_SELECTION
        required = {"competition", "season", "team", "player", "match", "standings", "top_scorers"}
        for et in required:
            assert et in PROVIDER_SELECTION
