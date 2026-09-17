"""Database models — imports all models for Base.metadata.create_all()."""

from db.base import Base

from db.models.competition import Competition
from db.models.season import Season
from db.models.team import Team
from db.models.venue import Venue
from db.models.coach import Coach
from db.models.team_coach import TeamCoach
from db.models.player import Player
from db.models.team_squad import TeamSquad
from db.models.referee import Referee
from db.models.match import Match
from db.models.match_event import MatchEvent
from db.models.match_lineup import MatchLineup
from db.models.match_statistic import MatchStatistic
from db.models.standing_snapshot import StandingSnapshot
from db.models.standing_row import StandingRow
from db.models.transfer import Transfer
from db.models.player_season_stat import PlayerSeasonStat
from db.models.data_source import DataSource
from db.models.external_id import ExternalId
from db.models.import_job import ImportJob
from db.models.match_correction import MatchCorrection
