"""add player photo url."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import DateTime, Text


# revision identifiers, used by Alembic.
revision = "0002_player_photo_url"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Player Photo ───
    op.add_column("players", sa.Column("photo_url", Text, nullable=True))
    op.add_column("players", sa.Column("photo_updated_at", DateTime, nullable=True))


def downgrade() -> None:
    op.drop_column("players", "photo_updated_at")
    op.drop_column("players", "photo_url")
