"""Transfer record."""

from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    from_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    to_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    transfer_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    transfer_fee: Mapped[str | None] = mapped_column(Text, nullable=True)
    season_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────

    player: Mapped["Player"] = relationship(back_populates="transfers")
    from_team: Mapped["Team"] = relationship(
        foreign_keys=[from_team_id], back_populates="outgoing_transfers"
    )
    to_team: Mapped["Team"] = relationship(
        foreign_keys=[to_team_id], back_populates="incoming_transfers"
    )
    season: Mapped["Season | None"] = relationship(back_populates="transfers")
