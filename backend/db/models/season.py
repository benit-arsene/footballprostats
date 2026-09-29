"""Season model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competition_id: Mapped[int] = mapped_column(Integer, ForeignKey("competitions.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    availability_status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_imported")
    import_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_import_attempt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────

    competition: Mapped["Competition"] = relationship(back_populates="seasons")
    matches: Mapped[list["Match"]] = relationship(back_populates="season")
    standing_snapshots: Mapped[list["StandingSnapshot"]] = relationship(back_populates="season")
    squad_memberships: Mapped[list["TeamSquad"]] = relationship(back_populates="season")
    team_coaches: Mapped[list["TeamCoach"]] = relationship(back_populates="season")
    transfers: Mapped[list["Transfer"]] = relationship(back_populates="season")
    player_season_stats: Mapped[list["PlayerSeasonStat"]] = relationship(back_populates="season")
