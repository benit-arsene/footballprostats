"""Match lineup model."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class MatchLineup(Base):
    __tablename__ = "match_lineups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    position: Mapped[str] = mapped_column(String(10), nullable=False, default="Unknown")
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ─── Relationships ────────────────────────────────────────────────

    match: Mapped["Match"] = relationship(back_populates="lineups")
    team: Mapped["Team"] = relationship(back_populates="lineups")
    player: Mapped["Player"] = relationship(back_populates="lineups")
