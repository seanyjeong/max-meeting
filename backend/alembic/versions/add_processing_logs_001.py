"""Add STT and LLM processing logs tables.

Revision ID: add_processing_logs_001
Revises: fix_schema_mismatch_001
Create Date: 2025-01-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_processing_logs_001"
down_revision: Union[str, None] = "20260130_time_seg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create stt_logs table
    op.create_table(
        "stt_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recording_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=True),
        sa.Column("total_chunks", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
        sa.Column("audio_file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("transcript_length", sa.Integer(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recordings.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_stt_logs_recording", "stt_logs", ["recording_id"], unique=False)
    op.create_index("idx_stt_logs_created", "stt_logs", ["created_at"], unique=False)
    op.create_index("idx_stt_logs_event", "stt_logs", ["event_type"], unique=False)

    # Create llm_logs table
    op.create_table(
        "llm_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meeting_id", sa.Integer(), nullable=True),
        sa.Column("agenda_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("prompt_length", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("response_length", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["meetings.id"],
        ),
        sa.ForeignKeyConstraint(
            ["agenda_id"],
            ["agendas.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_llm_logs_meeting", "llm_logs", ["meeting_id"], unique=False)
    op.create_index("idx_llm_logs_created", "llm_logs", ["created_at"], unique=False)
    op.create_index("idx_llm_logs_operation", "llm_logs", ["operation"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_llm_logs_operation", table_name="llm_logs")
    op.drop_index("idx_llm_logs_created", table_name="llm_logs")
    op.drop_index("idx_llm_logs_meeting", table_name="llm_logs")
    op.drop_table("llm_logs")

    op.drop_index("idx_stt_logs_event", table_name="stt_logs")
    op.drop_index("idx_stt_logs_created", table_name="stt_logs")
    op.drop_index("idx_stt_logs_recording", table_name="stt_logs")
    op.drop_table("stt_logs")
