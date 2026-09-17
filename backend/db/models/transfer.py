"""Transfer record."""

from datetime import datetime

from sqlalchemy import Date, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    from_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    to_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    transfer_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    transfer_fee: Mapped[str | None] = mapped_column(Text, nullable=True)
    season_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
