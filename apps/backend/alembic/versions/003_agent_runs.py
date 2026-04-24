"""add agent run audit table

Revision ID: 003
Revises: 002
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("child_id", sa.String(), sa.ForeignKey("children.id")),
        sa.Column("action_type", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("source_urls", sa.JSON()),
        sa.Column("sources", sa.JSON()),
        sa.Column("extracted_facts", sa.JSON()),
        sa.Column("draft", sa.JSON()),
        sa.Column("pattern_summary", sa.JSON()),
        sa.Column("agent_steps", sa.JSON()),
        sa.Column("sponsor_statuses", sa.JSON()),
        sa.Column("approvals", sa.JSON()),
    )


def downgrade():
    op.drop_table("agent_runs")
