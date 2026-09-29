"""Match event model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class MatchEvent(Base):
    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    added_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    second_player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────

    match: Mapped["Match"] = relationship(back_populates="events")
    team: Mapped["Team"] = relationship(back_populates="match_events")
    player: Mapped["Player | None"] = relationship(
        foreign_keys=[player_id], back_populates="match_events"
    )
    second_player: Mapped["Player | None"] = relationship(
        foreign_keys=[second_player_id], back_populates="second_match_events"
    )
