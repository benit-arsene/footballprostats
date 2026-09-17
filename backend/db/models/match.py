"""Match model."""

from datetime import datetime

from sqlalchemy import Date, Float, Integer, String, Text, Time, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    competition_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    away_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    venue_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referee_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    kickoff_time: Mapped[Time | None] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correction_of_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
