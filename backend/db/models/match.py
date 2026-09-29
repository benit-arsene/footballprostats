"""Match model."""

from datetime import datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    competition_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("competitions.id"), nullable=True)
    season_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=True)
    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    venue_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("venues.id"), nullable=True)
    referee_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("referees.id"), nullable=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    kickoff_time: Mapped[Time | None] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correction_of_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("matches.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────

    competition: Mapped["Competition | None"] = relationship(back_populates="matches")
    season: Mapped["Season | None"] = relationship(back_populates="matches")
    home_team: Mapped["Team"] = relationship(
        foreign_keys=[home_team_id], back_populates="home_matches"
    )
    away_team: Mapped["Team"] = relationship(
        foreign_keys=[away_team_id], back_populates="away_matches"
    )
    venue: Mapped["Venue | None"] = relationship(back_populates="matches")
    referee: Mapped["Referee | None"] = relationship(back_populates="matches")
    correction_of: Mapped["Match | None"] = relationship()
    corrections: Mapped[list["Match"]] = relationship(remote_side=[id])
    events: Mapped[list["MatchEvent"]] = relationship(back_populates="match")
    lineups: Mapped[list["MatchLineup"]] = relationship(back_populates="match")
    statistics: Mapped[list["MatchStatistic"]] = relationship(back_populates="match")
