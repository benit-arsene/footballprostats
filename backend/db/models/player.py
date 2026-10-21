"""Player model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from db.models.match_event import MatchEvent


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False, default="Unknown")
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(10), nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    foot: Mapped[str | None] = mapped_column(String(10), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────

    match_events: Mapped[list["MatchEvent"]] = relationship(
        foreign_keys=[MatchEvent.player_id], back_populates="player"
    )
    second_match_events: Mapped[list["MatchEvent"]] = relationship(
        foreign_keys="MatchEvent.second_player_id", back_populates="second_player"
    )
    lineups: Mapped[list["MatchLineup"]] = relationship(back_populates="player")
    season_stats: Mapped[list["PlayerSeasonStat"]] = relationship(back_populates="player")
    squad_memberships: Mapped[list["TeamSquad"]] = relationship(back_populates="player")
    transfers: Mapped[list["Transfer"]] = relationship(back_populates="player")
