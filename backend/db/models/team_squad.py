"""Historical squad membership."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class TeamSquad(Base):
    __tablename__ = "team_squad"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=False)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────

    team: Mapped["Team"] = relationship(back_populates="squad")
    player: Mapped["Player"] = relationship(back_populates="squad_memberships")
    season: Mapped["Season"] = relationship(back_populates="squad_memberships")
