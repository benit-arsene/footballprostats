"""Historical coaching staff."""

from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class TeamCoach(Base):
    __tablename__ = "team_coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    coach_id: Mapped[int] = mapped_column(Integer, ForeignKey("coaches.id"), nullable=False)
    season_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=True)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────

    team: Mapped["Team"] = relationship(back_populates="coaches")
    coach: Mapped["Coach"] = relationship(back_populates="team_coaches")
    season: Mapped["Season | None"] = relationship(back_populates="team_coaches")
