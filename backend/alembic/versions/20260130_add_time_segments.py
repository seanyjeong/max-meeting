"""add_time_segments_to_agendas

Revision ID: 20260130_time_seg
Revises: 1683beaa9622
Create Date: 2026-01-30 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260130_time_seg'
down_revision: Union[str, Sequence[str], None] = 'fix_schema_mismatch_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add time_segments JSONB column to agendas table.

    This allows tracking multiple time ranges per agenda item,
    supporting meetings where topics are revisited.

    Structure: [{"start": 0, "end": 30}, {"start": 60, "end": 80}]
    """
    op.add_column(
        'agendas',
        sa.Column(
            'time_segments',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Array of time segments [{start, end}] for multi-segment support'
        )
    )

    # Optional: GIN index for JSON queries (uncomment if needed for performance)
    # op.create_index(
    #     'idx_agendas_time_segments',
    #     'agendas',
    #     ['time_segments'],
    #     postgresql_using='gin'
    # )


def downgrade() -> None:
    """Remove time_segments column from agendas table."""
    # op.drop_index('idx_agendas_time_segments', table_name='agendas')
    op.drop_column('agendas', 'time_segments')
