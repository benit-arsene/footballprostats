"""
Pydantic models for the Football Pro Stats API.

These mirror the frontend TypeScript types and define the JSON
contract between FastAPI and the Next.js frontend.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class APIErrorResponse(BaseModel):
    error: APIErrorDetail


class APIErrorDetail(BaseModel):
    code: str
    message: str


# ─── Enums ─────────────────────────────────────────────────────────────


class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    GOAL = "goal"
    OWN_GOAL = "own_goal"
    PENALTY_SCORED = "penalty_scored"
    PENALTY_MISSED = "penalty_missed"
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    SECOND_YELLOW_CARD = "second_yellow_card"
    SUBSTITUTION = "substitution"
    VAR_DECISION = "var_decision"
    KICKOFF = "kickoff"
    HALFTIME = "halftime"
    FULLTIME = "fulltime"
    EXTRA_TIME_START = "extra_time_start"
    PENALTY_SHOOTOUT = "penalty_shootout"


# ─── Shared summaries ─────────────────────────────────────────────────


class LeagueSummary(BaseModel):
    id: int
    name: str
    slug: str
    country: str
    logo_url: str


class TeamSummary(BaseModel):
    id: int
    name: str
    slug: str
    crest_url: str


class PlayerSummary(BaseModel):
    id: int
    name: str
    slug: str
    position: str
    number: Optional[int] = None
    nationality: str


# ─── Match ────────────────────────────────────────────────────────────


class MatchSummary(BaseModel):
    id: int
    slug: str
    status: MatchStatus
    minute: Optional[int] = None
    date: str
    kickoff_time: str
    venue: str
    league: LeagueSummary
    home_team: TeamSummary
    away_team: TeamSummary
    home_score: int
    away_score: int


class LineupPlayer(BaseModel):
    player: PlayerSummary
    position: str
    shirt_number: Optional[int] = None
    rating: Optional[float] = None


class MatchEvent(BaseModel):
    id: int
    minute: int
    added_time: Optional[int] = None
    type: EventType
    team: TeamSummary
    player: PlayerSummary
    second_player: Optional[PlayerSummary] = None
    detail: Optional[str] = None


class MatchStats(BaseModel):
    possession: tuple[int, int]
    shots: tuple[int, int]
    shots_on_target: tuple[int, int]
    corners: tuple[int, int]
    fouls: tuple[int, int]
    yellow_cards: tuple[int, int]
    red_cards: tuple[int, int]


class MatchDetail(MatchSummary):
    attendance: Optional[int] = None
    referee: str
    home_lineup: list[LineupPlayer] = []
    away_lineup: list[LineupPlayer] = []
    events: list[MatchEvent] = []
    stats: Optional[MatchStats] = None


class LiveMatchUpdate(BaseModel):
    match_id: int
    slug: str
    status: MatchStatus
    minute: int
    home_score: int
    away_score: int
    events: list[MatchEvent] = []
    last_event_id: int


# ─── Team ─────────────────────────────────────────────────────────────


class TeamProfile(BaseModel):
    id: int
    name: str
    slug: str
    short_name: str
    crest_url: str
    league: LeagueSummary
    founded: int
    venue: str
    coach: str
    squad: list[PlayerSummary] = []


# ─── Player ───────────────────────────────────────────────────────────


class CareerStats(BaseModel):
    appearances: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    minutes_played: int


class MatchLogEntry(BaseModel):
    match_id: int
    match_slug: str
    date: str
    opponent: str
    result: str
    goals: int
    assists: int
    rating: Optional[float] = None


class PlayerProfile(BaseModel):
    id: int
    name: str
    slug: str
    position: str
    number: Optional[int] = None
    nationality: str
    date_of_birth: str
    height_cm: Optional[int] = None
    foot: str
    team: TeamSummary
    career_stats: CareerStats
    match_logs: list[MatchLogEntry] = []


# ─── League ───────────────────────────────────────────────────────────


class StandingRow(BaseModel):
    position: int
    team: TeamSummary
    played: int
    won: int
    drawn: int
    lost: int
    gf: int
    ga: int
    gd: int
    points: int
    form: list[str] = []


class TopScorer(BaseModel):
    player: PlayerSummary
    team: TeamSummary
    goals: int
    assists: int


class LeagueProfile(BaseModel):
    id: int
    name: str
    slug: str
    country: str
    logo_url: str
    season: str
    standings: list[StandingRow] = []
    top_scorers: list[TopScorer] = []
    fixtures: list[MatchSummary] = []
