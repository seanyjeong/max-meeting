"""add_agenda_hierarchy

Revision ID: 1683beaa9622
Revises: e3b64dac2684
Create Date: 2026-01-29 14:56:02.605005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1683beaa9622'
down_revision: Union[str, Sequence[str], None] = 'e3b64dac2684'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add hierarchical structure to agendas table."""
    # Add parent_id column for self-referential hierarchy
    op.add_column('agendas', sa.Column('parent_id', sa.Integer(), nullable=True))

    # Add level column for caching depth (performance optimization)
    op.add_column('agendas', sa.Column('level', sa.Integer(), server_default='0', nullable=False))

    # Add foreign key constraint for parent_id
    op.create_foreign_key(
        'fk_agendas_parent_id',
        'agendas', 'agendas',
        ['parent_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add index for efficient queries on children by parent
    op.create_index('idx_agendas_parent_order', 'agendas', ['parent_id', 'order_num'])


def downgrade() -> None:
    """Remove hierarchical structure from agendas table."""
    op.drop_index('idx_agendas_parent_order', table_name='agendas')
    op.drop_constraint('fk_agendas_parent_id', 'agendas', type_='foreignkey')
    op.drop_column('agendas', 'level')
    op.drop_column('agendas', 'parent_id')
