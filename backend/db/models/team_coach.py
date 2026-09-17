"""Historical coaching staff."""

from datetime import datetime

from sqlalchemy import Date, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class TeamCoach(Base):
    __tablename__ = "team_coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    coach_id: Mapped[int] = mapped_column(Integer, nullable=False)
    season_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
