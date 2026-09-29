"""Team model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    crest_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    founded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("venues.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────

    venue: Mapped["Venue | None"] = relationship(back_populates="teams")
    home_matches: Mapped[list["Match"]] = relationship(
        foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    away_matches: Mapped[list["Match"]] = relationship(
        foreign_keys="Match.away_team_id", back_populates="away_team"
    )
    match_events: Mapped[list["MatchEvent"]] = relationship(back_populates="team")
    lineups: Mapped[list["MatchLineup"]] = relationship(back_populates="team")
    match_statistics: Mapped[list["MatchStatistic"]] = relationship(back_populates="team")
    standing_rows: Mapped[list["StandingRow"]] = relationship(back_populates="team")
    player_season_stats: Mapped[list["PlayerSeasonStat"]] = relationship(back_populates="team")
    squad: Mapped[list["TeamSquad"]] = relationship(back_populates="team")
    coaches: Mapped[list["TeamCoach"]] = relationship(back_populates="team")
    outgoing_transfers: Mapped[list["Transfer"]] = relationship(
        foreign_keys="Transfer.from_team_id", back_populates="from_team"
    )
    incoming_transfers: Mapped[list["Transfer"]] = relationship(
        foreign_keys="Transfer.to_team_id", back_populates="to_team"
    )
