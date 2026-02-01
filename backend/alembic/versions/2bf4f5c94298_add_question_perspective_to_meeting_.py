"""add question_perspective to meeting_types

Revision ID: 2bf4f5c94298
Revises: add_processing_logs_001
Create Date: 2026-02-01 06:43:53.624974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2bf4f5c94298'
down_revision: Union[str, Sequence[str], None] = 'add_processing_logs_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add question_perspective column to meeting_types table."""
    op.add_column('meeting_types', sa.Column('question_perspective', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove question_perspective column from meeting_types table."""
    op.drop_column('meeting_types', 'question_perspective')
