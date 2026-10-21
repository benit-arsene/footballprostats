"""Persistent daily quota ledger for image ingestion."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ImageIngestionQuota(Base):
    __tablename__ = "image_ingestion_quota"

    utc_date: Mapped[date] = mapped_column(Date, primary_key=True)
    daily_cap: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )