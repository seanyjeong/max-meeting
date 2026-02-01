"""add name field to meeting_attendees and make contact_id nullable

Revision ID: acd7c5318ffd
Revises: 2bf4f5c94298
Create Date: 2026-02-01 08:07:39.867308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'acd7c5318ffd'
down_revision: Union[str, Sequence[str], None] = '2bf4f5c94298'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add name field and make contact_id nullable for ad-hoc attendees."""
    # Add name field for ad-hoc attendees
    op.add_column('meeting_attendees', sa.Column('name', sa.String(length=100), nullable=True))

    # Make contact_id nullable
    op.alter_column('meeting_attendees', 'contact_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)


def downgrade() -> None:
    """Remove name field and make contact_id required again."""
    # Make contact_id required again
    op.alter_column('meeting_attendees', 'contact_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)

    # Remove name field
    op.drop_column('meeting_attendees', 'name')
