"""initial schema

Revision ID: c27eaefe701b
Revises:
Create Date: 2026-01-28 17:49:39.704053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c27eaefe701b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for MAX Meeting."""

    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # contacts
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('phone_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('email_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('organization', sa.String(100), nullable=True),
        sa.Column('position', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_contacts_name_trgm', 'contacts', ['name'], postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})

    # meeting_types
    op.create_table(
        'meeting_types',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agenda_template', postgresql.JSONB(), nullable=True),
        sa.Column('default_duration_minutes', sa.Integer(), default=60),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # meetings
    op.create_table(
        'meetings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('type_id', sa.Integer(), sa.ForeignKey('meeting_types.id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('status', sa.String(20), default='draft', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_meetings_type_status', 'meetings', ['type_id', 'status'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_meetings_scheduled_at', 'meetings', ['scheduled_at'], postgresql_where=sa.text('deleted_at IS NULL'))

    # meeting_attendees
    op.create_table(
        'meeting_attendees',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contact_id', sa.Integer(), sa.ForeignKey('contacts.id'), nullable=False),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('is_present', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_meeting_attendees_meeting', 'meeting_attendees', ['meeting_id'])

    # agendas
    op.create_table(
        'agendas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_num', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_agendas_meeting_order', 'agendas', ['meeting_id', 'order_num'])

    # agenda_questions
    op.create_table(
        'agenda_questions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('agenda_id', sa.Integer(), sa.ForeignKey('agendas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_num', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('source', sa.String(20), default='manual', nullable=False),
        sa.Column('is_answered', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # recordings
    op.create_table(
        'recordings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('format', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_recordings_meeting', 'recordings', ['meeting_id'])

    # transcripts
    op.create_table(
        'transcripts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('recording_id', sa.Integer(), sa.ForeignKey('recordings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('full_text', sa.Text(), nullable=True),
        sa.Column('segments', postgresql.JSONB(), nullable=True),
        sa.Column('language', sa.String(10), default='ko'),
        sa.Column('confidence_avg', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # manual_notes
    op.create_table(
        'manual_notes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agenda_id', sa.Integer(), sa.ForeignKey('agendas.id', ondelete='SET NULL'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # sketches
    op.create_table(
        'sketches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agenda_id', sa.Integer(), sa.ForeignKey('agendas.id', ondelete='SET NULL'), nullable=True),
        sa.Column('json_data', postgresql.JSONB(), nullable=False),
        sa.Column('thumbnail_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # meeting_results
    op.create_table(
        'meeting_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), default=1, nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_points', postgresql.JSONB(), nullable=True),
        sa.Column('generated_by', sa.String(50), default='gemini-flash'),
        sa.Column('is_final', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_meeting_results_meeting_version', 'meeting_results', ['meeting_id', 'version'])

    # meeting_decisions
    op.create_table(
        'meeting_decisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('result_id', sa.Integer(), sa.ForeignKey('meeting_results.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agenda_id', sa.Integer(), sa.ForeignKey('agendas.id', ondelete='SET NULL'), nullable=True),
        sa.Column('decision_type', sa.String(20), default='decision', nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # agenda_discussions
    op.create_table(
        'agenda_discussions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('result_id', sa.Integer(), sa.ForeignKey('meeting_results.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agenda_id', sa.Integer(), sa.ForeignKey('agendas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_points', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # action_items
    op.create_table(
        'action_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('result_id', sa.Integer(), sa.ForeignKey('meeting_results.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agenda_id', sa.Integer(), sa.ForeignKey('agendas.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assignee_id', sa.Integer(), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('priority', sa.String(20), default='medium', nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_action_items_assignee_status', 'action_items', ['assignee_id', 'status'])

    # task_trackings
    op.create_table(
        'task_trackings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('recording_id', sa.Integer(), sa.ForeignKey('recordings.id', ondelete='CASCADE'), nullable=True),
        sa.Column('task_id', sa.String(100), nullable=False, unique=True),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_task_trackings_status', 'task_trackings', ['status'])

    # audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.String(50), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('request_id', postgresql.UUID(), nullable=True),
        sa.Column('event', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(50), nullable=True),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), default='success', nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
    )
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_user', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_event', 'audit_logs', ['event'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('audit_logs')
    op.drop_table('task_trackings')
    op.drop_table('action_items')
    op.drop_table('agenda_discussions')
    op.drop_table('meeting_decisions')
    op.drop_table('meeting_results')
    op.drop_table('sketches')
    op.drop_table('manual_notes')
    op.drop_table('transcripts')
    op.drop_table('recordings')
    op.drop_table('agenda_questions')
    op.drop_table('agendas')
    op.drop_table('meeting_attendees')
    op.drop_table('meetings')
    op.drop_table('meeting_types')
    op.drop_table('contacts')

    op.execute('DROP EXTENSION IF EXISTS "pg_trgm"')
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
