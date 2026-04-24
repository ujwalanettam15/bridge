"""add intent context and confirmation fields

Revision ID: 002
Revises: 001
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("intent_logs", sa.Column("context", sa.JSON(), nullable=True))
    op.add_column("intent_logs", sa.Column("confirmed_label", sa.String(), nullable=True))
    op.add_column("intent_logs", sa.Column("confirmed_at", sa.DateTime(), nullable=True))
    op.add_column("intent_logs", sa.Column("spoken_phrase", sa.String(), nullable=True))


def downgrade():
    op.drop_column("intent_logs", "spoken_phrase")
    op.drop_column("intent_logs", "confirmed_at")
    op.drop_column("intent_logs", "confirmed_label")
    op.drop_column("intent_logs", "context")
