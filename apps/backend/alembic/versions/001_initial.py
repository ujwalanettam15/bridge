"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "children",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String()),
        sa.Column("age", sa.Float()),
        sa.Column("behavior_profile", sa.JSON()),
        sa.Column("preferred_symbols", sa.JSON()),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("child_id", sa.String(), sa.ForeignKey("children.id")),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("intent_log", sa.JSON()),
    )
    op.create_table(
        "intent_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("child_id", sa.String(), sa.ForeignKey("children.id")),
        sa.Column("timestamp", sa.DateTime()),
        sa.Column("gesture_vector", sa.JSON()),
        sa.Column("audio_transcript", sa.String()),
        sa.Column("ranked_intents", sa.JSON()),
    )


def downgrade():
    op.drop_table("intent_logs")
    op.drop_table("sessions")
    op.drop_table("children")
