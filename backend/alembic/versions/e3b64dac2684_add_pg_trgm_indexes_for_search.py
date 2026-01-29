"""add_pg_trgm_indexes_for_search

Revision ID: e3b64dac2684
Revises: c27eaefe701b
Create Date: 2026-01-28 18:27:06.438971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b64dac2684'
down_revision: Union[str, Sequence[str], None] = 'c27eaefe701b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add GIN indexes for pg_trgm full-text search."""

    # Add GIN index on meeting_results.summary for full-text search
    op.create_index(
        'ix_meeting_results_summary_trgm',
        'meeting_results',
        ['summary'],
        postgresql_using='gin',
        postgresql_ops={'summary': 'gin_trgm_ops'}
    )

    # Add GIN index on transcripts.full_text for full-text search
    op.create_index(
        'ix_transcripts_full_text_trgm',
        'transcripts',
        ['full_text'],
        postgresql_using='gin',
        postgresql_ops={'full_text': 'gin_trgm_ops'}
    )


def downgrade() -> None:
    """Remove GIN indexes for pg_trgm full-text search."""

    # Remove indexes in reverse order
    op.drop_index('ix_transcripts_full_text_trgm', table_name='transcripts')
    op.drop_index('ix_meeting_results_summary_trgm', table_name='meeting_results')
