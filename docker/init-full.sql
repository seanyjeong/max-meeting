-- MAX Meeting 전체 스키마 초기화
-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enum 타입
DO $$ BEGIN CREATE TYPE meeting_status AS ENUM ('DRAFT', 'IN_PROGRESS', 'COMPLETED'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE agenda_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE decision_type AS ENUM ('APPROVED', 'REJECTED', 'POSTPONED'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE action_item_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE action_item_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE recording_status AS ENUM ('PENDING', 'UPLOADING', 'PROCESSING', 'COMPLETED', 'FAILED'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE transcript_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'); EXCEPTION WHEN duplicate_object THEN null; END $$;

-- meeting_types
CREATE TABLE IF NOT EXISTS meeting_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- contacts
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50),
    organization VARCHAR(100),
    phone_encrypted BYTEA,
    email_encrypted BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- meetings
CREATE TABLE IF NOT EXISTS meetings (
    id SERIAL PRIMARY KEY,
    type_id INTEGER REFERENCES meeting_types(id),
    title VARCHAR(200) NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    location VARCHAR(200),
    status meeting_status DEFAULT 'DRAFT',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- agendas
CREATE TABLE IF NOT EXISTS agendas (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    order_num INTEGER DEFAULT 0,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status agenda_status DEFAULT 'PENDING',
    started_at_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- agenda_questions
CREATE TABLE IF NOT EXISTS agenda_questions (
    id SERIAL PRIMARY KEY,
    agenda_id INTEGER NOT NULL REFERENCES agendas(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    order_num INTEGER DEFAULT 0,
    is_generated BOOLEAN DEFAULT FALSE,
    answered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- meeting_attendees
CREATE TABLE IF NOT EXISTS meeting_attendees (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES contacts(id),
    attended BOOLEAN DEFAULT FALSE,
    speaker_label VARCHAR(50),
    UNIQUE(meeting_id, contact_id)
);

-- recordings
CREATE TABLE IF NOT EXISTS recordings (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    duration_seconds INTEGER,
    mime_type VARCHAR(100),
    sample_rate INTEGER,
    channels INTEGER,
    status recording_status DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- transcripts
CREATE TABLE IF NOT EXISTS transcripts (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    recording_id INTEGER REFERENCES recordings(id),
    content TEXT,
    segments JSONB,
    language VARCHAR(10) DEFAULT 'ko',
    word_count INTEGER,
    confidence_avg FLOAT,
    stt_model VARCHAR(100),
    processing_time_seconds FLOAT,
    status transcript_status DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- manual_notes
CREATE TABLE IF NOT EXISTS manual_notes (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agenda_id INTEGER REFERENCES agendas(id),
    content TEXT,
    timestamp_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- sketches
CREATE TABLE IF NOT EXISTS sketches (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agenda_id INTEGER REFERENCES agendas(id),
    svg_file_path VARCHAR(500),
    json_data JSONB,
    extracted_text TEXT,
    thumbnail_path VARCHAR(500),
    timestamp_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- meeting_results
CREATE TABLE IF NOT EXISTS meeting_results (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    summary TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(meeting_id, version)
);

-- agenda_discussions
CREATE TABLE IF NOT EXISTS agenda_discussions (
    id SERIAL PRIMARY KEY,
    agenda_id INTEGER NOT NULL REFERENCES agendas(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_llm_generated BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- meeting_decisions
CREATE TABLE IF NOT EXISTS meeting_decisions (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agenda_id INTEGER REFERENCES agendas(id),
    content TEXT NOT NULL,
    decision_type decision_type DEFAULT 'APPROVED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- action_items
CREATE TABLE IF NOT EXISTS action_items (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agenda_id INTEGER REFERENCES agendas(id),
    assignee_id INTEGER REFERENCES contacts(id),
    content TEXT NOT NULL,
    due_date DATE,
    priority action_item_priority DEFAULT 'MEDIUM',
    status action_item_status DEFAULT 'PENDING',
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- task_trackings
CREATE TABLE IF NOT EXISTS task_trackings (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    action_item_id INTEGER REFERENCES action_items(id),
    status VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INTEGER,
    details JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_meetings_scheduled ON meetings(scheduled_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_meetings_type_status ON meetings(type_id, status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_agendas_meeting ON agendas(meeting_id, order_num) WHERE deleted_at IS NULL;

-- 기본 회의 타입
INSERT INTO meeting_types (name) VALUES ('북부'), ('전국'), ('일산') ON CONFLICT (name) DO NOTHING;

SELECT '스키마 초기화 완료!' as result;
