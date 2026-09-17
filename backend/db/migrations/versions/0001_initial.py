"""initial database schema."""

from datetime import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy import DateTime, Integer, String, Text, Boolean, Date, Time, Float


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Competitions ───
    op.create_table(
        "competitions",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("name", String(255), nullable=False),
        sa.Column("slug", String(255), unique=True, nullable=False),
        sa.Column("country", String(255), nullable=True),
        sa.Column("logo_url", Text, nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )

    # ─── Seasons ───
    op.create_table(
        "seasons",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("competition_id", Integer, nullable=False),
        sa.Column("label", String(50), nullable=False),
        sa.Column("start_date", DateTime, nullable=True),
        sa.Column("end_date", DateTime, nullable=True),
        sa.Column("availability_status", String(20), nullable=False, default="not_imported"),
        sa.Column("import_job_id", Integer, nullable=True),
        sa.Column("last_import_attempt", DateTime, nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )
    op.create_unique_constraint("uq_seasons_competition_label", "seasons", ["competition_id", "label"])

    # ─── Venues ───
    op.create_table(
        "venues",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("name", String(255), nullable=False),
        sa.Column("city", String(255), nullable=True),
        sa.Column("capacity", Integer, nullable=True),
        sa.Column("address", Text, nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )

    # ─── Teams ───
    op.create_table(
        "teams",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("name", String(255), nullable=False),
        sa.Column("slug", String(255), unique=True, nullable=False),
        sa.Column("short_name", String(100), nullable=True),
        sa.Column("crest_url", Text, nullable=True),
        sa.Column("founded", Integer, nullable=True),
        sa.Column("venue_id", Integer, ForeignKey("venues.id"), nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )

    # ─── Coaches ───
    op.create_table(
        "coaches",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("name", String(255), nullable=False),
        sa.Column("nationality", String(255), nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )

    # ─── Team Coaches ───
    op.create_table(
        "team_coaches",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("coach_id", Integer, ForeignKey("coaches.id"), nullable=False),
        sa.Column("season_id", Integer, ForeignKey("seasons.id"), nullable=True),
        sa.Column("start_date", Date, nullable=False),
        sa.Column("end_date", Date, nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )

    # ─── Players ───
    op.create_table(
        "players",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("name", String(255), nullable=False),
        sa.Column("slug", String(255), unique=True, nullable=False),
        sa.Column("position", String(100), nullable=False, default="Unknown"),
        sa.Column("number", Integer, nullable=True),
        sa.Column("nationality", String(255), nullable=True),
        sa.Column("date_of_birth", String(10), nullable=True),
        sa.Column("height_cm", Integer, nullable=True),
        sa.Column("foot", String(10), nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )

    # ─── Team Squad ───
    op.create_table(
        "team_squad",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("player_id", Integer, ForeignKey("players.id"), nullable=False),
        sa.Column("season_id", Integer, ForeignKey("seasons.id"), nullable=False),
        sa.Column("shirt_number", Integer, nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    )
    op.create_unique_constraint("uq_team_squad", "team_squad", ["team_id", "player_id", "season_id"])

    # ─── Referees ───
    op.create_table(
        "referees",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("name", String(255), nullable=False),
        sa.Column("nationality", String(255), nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )

    # ─── Matches ───
    op.create_table(
        "matches",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("slug", String(500), unique=True, nullable=False),
        sa.Column("competition_id", Integer, ForeignKey("competitions.id"), nullable=True),
        sa.Column("season_id", Integer, ForeignKey("seasons.id"), nullable=True),
        sa.Column("home_team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("venue_id", Integer, ForeignKey("venues.id"), nullable=True),
        sa.Column("referee_id", Integer, ForeignKey("referees.id"), nullable=True),
        sa.Column("date", Date, nullable=False),
        sa.Column("kickoff_time", Time, nullable=True),
        sa.Column("status", String(20), nullable=False, default="scheduled"),
        sa.Column("minute", Integer, nullable=True),
        sa.Column("home_score", Integer, nullable=False, default=0),
        sa.Column("away_score", Integer, nullable=False, default=0),
        sa.Column("attendance", Integer, nullable=True),
        sa.Column("correction_of_id", Integer, ForeignKey("matches.id"), nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )

    # ─── Match Events ───
    op.create_table(
        "match_events",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("match_id", Integer, ForeignKey("matches.id"), nullable=False),
        sa.Column("minute", Integer, nullable=False),
        sa.Column("added_time", Integer, nullable=True),
        sa.Column("type", String(50), nullable=False),
        sa.Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("player_id", Integer, ForeignKey("players.id"), nullable=True),
        sa.Column("second_player_id", Integer, ForeignKey("players.id"), nullable=True),
        sa.Column("detail", Text, nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    )
    op.create_unique_constraint("uq_match_events", "match_events", ["match_id", "id"])

    # ─── Match Lineups ───
    op.create_table(
        "match_lineups",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("match_id", Integer, ForeignKey("matches.id"), nullable=False),
        sa.Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("player_id", Integer, ForeignKey("players.id"), nullable=False),
        sa.Column("position", String(10), nullable=False, default="Unknown"),
        sa.Column("shirt_number", Integer, nullable=True),
        sa.Column("rating", Float, nullable=True),
    )
    op.create_unique_constraint("uq_match_lineups", "match_lineups", ["match_id", "team_id", "player_id"])

    # ─── Match Statistics ───
    op.create_table(
        "match_statistics",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("match_id", Integer, ForeignKey("matches.id"), nullable=False),
        sa.Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("possession_home", Integer, nullable=True),
        sa.Column("possession_away", Integer, nullable=True),
        sa.Column("shots", Integer, nullable=True),
        sa.Column("shots_on_target", Integer, nullable=True),
        sa.Column("corners", Integer, nullable=True),
        sa.Column("fouls", Integer, nullable=True),
        sa.Column("yellow_cards", Integer, nullable=True),
        sa.Column("red_cards", Integer, nullable=True),
    )
    op.create_unique_constraint("uq_match_statistics", "match_statistics", ["match_id", "team_id"])

    # ─── Standing Snapshots ───
    op.create_table(
        "standing_snapshots",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("season_id", Integer, ForeignKey("seasons.id"), nullable=False),
        sa.Column("matchday", Integer, nullable=True),
        sa.Column("label", String(100), nullable=False),
        sa.Column("snapshot_date", DateTime, nullable=True),
        sa.Column("last_updated", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    )

    # ─── Standing Rows ───
    op.create_table(
        "standing_rows",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("standing_snapshot_id", Integer, ForeignKey("standing_snapshots.id"), nullable=False),
        sa.Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("position", Integer, nullable=False),
        sa.Column("played", Integer, nullable=False, default=0),
        sa.Column("won", Integer, nullable=False, default=0),
        sa.Column("drawn", Integer, nullable=False, default=0),
        sa.Column("lost", Integer, nullable=False, default=0),
        sa.Column("goals_for", Integer, nullable=False, default=0),
        sa.Column("goals_against", Integer, nullable=False, default=0),
        sa.Column("goal_difference", Integer, nullable=False, default=0),
        sa.Column("points", Integer, nullable=False, default=0),
        sa.Column("form", String(100), nullable=False, default=""),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    )
    op.create_unique_constraint("uq_standing_rows", "standing_rows", ["standing_snapshot_id", "team_id"])

    # ─── Transfers ───
    op.create_table(
        "transfers",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("player_id", Integer, ForeignKey("players.id"), nullable=False),
        sa.Column("from_team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("to_team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("transfer_date", Date, nullable=True),
        sa.Column("transfer_fee", Text, nullable=True),
        sa.Column("season_id", Integer, ForeignKey("seasons.id"), nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    )

    # ─── Player Season Stats ───
    op.create_table(
        "player_season_stats",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("player_id", Integer, ForeignKey("players.id"), nullable=False),
        sa.Column("season_id", Integer, ForeignKey("seasons.id"), nullable=False),
        sa.Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
        sa.Column("appearances", Integer, nullable=False, default=0),
        sa.Column("goals", Integer, nullable=False, default=0),
        sa.Column("assists", Integer, nullable=False, default=0),
        sa.Column("yellow_cards", Integer, nullable=False, default=0),
        sa.Column("red_cards", Integer, nullable=False, default=0),
        sa.Column("minutes_played", Integer, nullable=False, default=0),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    )
    op.create_unique_constraint("uq_player_season_stats", "player_season_stats", ["player_id", "season_id", "team_id"])

    # ─── Data Sources ───
    op.create_table(
        "data_sources",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("name", String(255), nullable=False),
        sa.Column("base_url", Text, nullable=True),
        sa.Column("is_active", Boolean, default=True, nullable=False),
        sa.Column("quota_limit", Integer, nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
    )

    # ─── External IDs ───
    op.create_table(
        "external_ids",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("entity_type", String(30), nullable=False),
        sa.Column("provider", String(100), nullable=False),
        sa.Column("external_id", String(255), nullable=False),
        sa.Column("competition_id", Integer, nullable=True),
        sa.Column("season_id", Integer, nullable=True),
        sa.Column("team_id", Integer, nullable=True),
        sa.Column("player_id", Integer, nullable=True),
        sa.Column("match_id", Integer, nullable=True),
        sa.Column("last_verified", DateTime, nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    )
    op.create_unique_constraint("uq_external_ids", "external_ids", ["entity_type", "provider", "external_id"])

    # ─── Import Jobs ───
    op.create_table(
        "import_jobs",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("entity_type", String(50), nullable=False),
        sa.Column("data_source_id", Integer, ForeignKey("data_sources.id"), nullable=False),
        sa.Column("status", String(20), nullable=False, default="pending"),
        sa.Column("started_at", DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("completed_at", DateTime, nullable=True),
        sa.Column("records_processed", Integer, nullable=False, default=0),
        sa.Column("records_failed", Integer, nullable=False, default=0),
        sa.Column("error_message", Text, nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    )

    # ─── Match Corrections ───
    op.create_table(
        "match_corrections",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("match_id", Integer, ForeignKey("matches.id"), nullable=False),
        sa.Column("corrected_match_id", Integer, ForeignKey("matches.id"), nullable=False),
        sa.Column("reason", Text, nullable=True),
        sa.Column("source", String(255), nullable=True),
        sa.Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("match_corrections")
    op.drop_table("import_jobs")
    op.drop_table("external_ids")
    op.drop_table("data_sources")
    op.drop_table("player_season_stats")
    op.drop_table("transfers")
    op.drop_table("standing_rows")
    op.drop_table("standing_snapshots")
    op.drop_table("match_statistics")
    op.drop_table("match_lineups")
    op.drop_table("match_events")
    op.drop_table("matches")
    op.drop_table("referees")
    op.drop_table("team_squad")
    op.drop_table("players")
    op.drop_table("team_coaches")
    op.drop_table("coaches")
    op.drop_table("teams")
    op.drop_table("venues")
    op.drop_table("seasons")
    op.drop_table("competitions")
