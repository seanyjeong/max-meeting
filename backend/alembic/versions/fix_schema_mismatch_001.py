"""Fix schema mismatches between DB and backend models

Revision ID: fix_schema_mismatch_001
Revises: 1683beaa9622
Create Date: 2026-01-29

Fixes:
1. transcripts: Add meeting_id, chunk_index columns (model expects them)
2. recordings: Add original_filename, safe_filename, mime_type, checksum, retry_count
3. agenda_questions: Rename columns to match model (question_text->question, source->is_generated, is_answered->answered)
4. meeting_results: Add is_verified, verified_at, updated_at columns
5. sketches: Add svg_file_path, extracted_text, timestamp_seconds columns
6. action_items: Make result_id nullable (model allows null)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_schema_mismatch_001'
down_revision = '1683beaa9622'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. transcripts: Add meeting_id and chunk_index columns
    op.add_column('transcripts', sa.Column('meeting_id', sa.Integer(), nullable=True))
    op.add_column('transcripts', sa.Column('chunk_index', sa.Integer(), nullable=True))

    # Set meeting_id from recording's meeting_id for existing rows
    op.execute("""
        UPDATE transcripts t
        SET meeting_id = r.meeting_id
        FROM recordings r
        WHERE t.recording_id = r.id AND t.meeting_id IS NULL
    """)

    # Set chunk_index to 0 for existing rows
    op.execute("UPDATE transcripts SET chunk_index = 0 WHERE chunk_index IS NULL")

    # Make columns NOT NULL after backfill
    op.alter_column('transcripts', 'meeting_id', nullable=False)
    op.alter_column('transcripts', 'chunk_index', nullable=False)

    # Add foreign key and indexes
    op.create_foreign_key(
        'transcripts_meeting_id_fkey', 'transcripts', 'meetings',
        ['meeting_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index('idx_transcripts_meeting', 'transcripts', ['meeting_id'])
    op.create_index('idx_transcripts_recording', 'transcripts', ['recording_id', 'chunk_index'])

    # Drop old index if exists
    op.execute("DROP INDEX IF EXISTS ix_transcripts_full_text_trgm")

    # 2. recordings: Add missing columns
    op.add_column('recordings', sa.Column('original_filename', sa.String(200), nullable=True))
    op.add_column('recordings', sa.Column('safe_filename', sa.String(200), nullable=False, server_default=''))
    op.add_column('recordings', sa.Column('mime_type', sa.String(50), nullable=False, server_default='audio/webm'))
    op.add_column('recordings', sa.Column('checksum', sa.String(64), nullable=True))
    op.add_column('recordings', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))

    # 3. agenda_questions: Rename columns to match model
    # question_text -> question
    op.alter_column('agenda_questions', 'question_text', new_column_name='question')

    # source -> is_generated (convert 'llm' to True, 'manual' to False)
    op.add_column('agenda_questions', sa.Column('is_generated', sa.Boolean(), nullable=True))
    op.execute("UPDATE agenda_questions SET is_generated = (source = 'llm')")
    op.alter_column('agenda_questions', 'is_generated', nullable=False, server_default='true')
    op.drop_column('agenda_questions', 'source')

    # is_answered -> answered
    op.alter_column('agenda_questions', 'is_answered', new_column_name='answered')
    op.alter_column('agenda_questions', 'answered', nullable=False, server_default='false')

    # 4. meeting_results: Add missing columns
    op.add_column('meeting_results', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('meeting_results', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('meeting_results', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')))

    # 5. sketches: Add missing columns
    op.add_column('sketches', sa.Column('svg_file_path', sa.String(500), nullable=True))
    op.add_column('sketches', sa.Column('extracted_text', sa.Text(), nullable=True))
    op.add_column('sketches', sa.Column('timestamp_seconds', sa.Integer(), nullable=True))

    # Make json_data nullable (model allows null)
    op.alter_column('sketches', 'json_data', nullable=True)

    # 6. action_items: Make result_id nullable and add meeting_id constraint
    op.alter_column('action_items', 'result_id', nullable=True)

    # Add content column if it doesn't have data
    op.execute("""
        UPDATE action_items
        SET content = COALESCE(title, '') || CASE WHEN description IS NOT NULL THEN ' - ' || description ELSE '' END
        WHERE content IS NULL OR content = ''
    """)


def downgrade() -> None:
    # 6. action_items: Restore result_id NOT NULL
    op.alter_column('action_items', 'result_id', nullable=False)

    # 5. sketches: Drop added columns
    op.alter_column('sketches', 'json_data', nullable=False)
    op.drop_column('sketches', 'timestamp_seconds')
    op.drop_column('sketches', 'extracted_text')
    op.drop_column('sketches', 'svg_file_path')

    # 4. meeting_results: Drop added columns
    op.drop_column('meeting_results', 'updated_at')
    op.drop_column('meeting_results', 'verified_at')
    op.drop_column('meeting_results', 'is_verified')

    # 3. agenda_questions: Restore original column names
    op.alter_column('agenda_questions', 'answered', new_column_name='is_answered')
    op.add_column('agenda_questions', sa.Column('source', sa.String(20), nullable=True))
    op.execute("UPDATE agenda_questions SET source = CASE WHEN is_generated THEN 'llm' ELSE 'manual' END")
    op.alter_column('agenda_questions', 'source', nullable=False)
    op.drop_column('agenda_questions', 'is_generated')
    op.alter_column('agenda_questions', 'question', new_column_name='question_text')

    # 2. recordings: Drop added columns
    op.drop_column('recordings', 'retry_count')
    op.drop_column('recordings', 'checksum')
    op.drop_column('recordings', 'mime_type')
    op.drop_column('recordings', 'safe_filename')
    op.drop_column('recordings', 'original_filename')

    # 1. transcripts: Drop added columns
    op.drop_index('idx_transcripts_recording', table_name='transcripts')
    op.drop_index('idx_transcripts_meeting', table_name='transcripts')
    op.drop_constraint('transcripts_meeting_id_fkey', 'transcripts', type_='foreignkey')
    op.drop_column('transcripts', 'chunk_index')
    op.drop_column('transcripts', 'meeting_id')
