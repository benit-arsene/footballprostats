"""add image ingestion daily quota ledger."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Date, DateTime, Integer


revision = "0003_image_ingestion_quota"
down_revision = "0002_player_photo_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "image_ingestion_quota",
        sa.Column("utc_date", Date, primary_key=True),
        sa.Column("daily_cap", Integer, nullable=False),
        sa.Column("reserved", Integer, nullable=False, server_default="0"),
        sa.Column("used", Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("image_ingestion_quota")