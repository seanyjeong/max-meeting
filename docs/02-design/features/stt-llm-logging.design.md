# Design: STT/LLM 로깅 시스템

## 개요

| 항목 | 내용 |
|------|------|
| **Feature ID** | stt-llm-logging |
| **Plan 참조** | `docs/01-plan/features/stt-llm-logging.plan.md` |
| **생성일** | 2025-01-31 |
| **상태** | Design |

## 아키텍처

```
┌─────────────────┐     ┌─────────────────┐
│   stt.py Task   │     │   llm.py Task   │
│  (Celery Worker)│     │  (Celery Worker)│
└────────┬────────┘     └────────┬────────┘
         │                       │
         │ log_stt_event()       │ log_llm_event()
         ▼                       ▼
┌─────────────────────────────────────────┐
│         ProcessingLogService            │
│  (app/services/processing_log.py)       │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│              PostgreSQL                 │
│  ┌──────────────┐  ┌──────────────┐    │
│  │  stt_logs    │  │  llm_logs    │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
```

## 데이터베이스 스키마

### 1. stt_logs 테이블

```sql
CREATE TABLE stt_logs (
    id SERIAL PRIMARY KEY,
    recording_id INTEGER NOT NULL REFERENCES recordings(id),
    task_id VARCHAR(255),

    -- Processing info
    event_type VARCHAR(50) NOT NULL,  -- 'start', 'chunk_complete', 'complete', 'error'
    chunk_index INTEGER,
    total_chunks INTEGER,

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,

    -- Audio info
    audio_duration_seconds FLOAT,
    audio_file_size_bytes BIGINT,

    -- Result
    transcript_length INTEGER,
    word_count INTEGER,

    -- Error info
    error_type VARCHAR(100),
    error_message TEXT,
    error_context JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_stt_logs_recording ON stt_logs(recording_id);
CREATE INDEX idx_stt_logs_created ON stt_logs(created_at);
CREATE INDEX idx_stt_logs_event ON stt_logs(event_type);
```

### 2. llm_logs 테이블

```sql
CREATE TABLE llm_logs (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id),
    agenda_id INTEGER REFERENCES agendas(id),
    task_id VARCHAR(255),

    -- Request info
    event_type VARCHAR(50) NOT NULL,  -- 'start', 'complete', 'error'
    operation VARCHAR(50) NOT NULL,   -- 'summary', 'questions', 'agenda_parse'
    provider VARCHAR(50),             -- 'gemini', 'openai'
    model VARCHAR(100),

    -- Input metrics
    prompt_tokens INTEGER,
    prompt_length INTEGER,

    -- Output metrics
    completion_tokens INTEGER,
    response_length INTEGER,

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,

    -- Cost estimation
    estimated_cost_usd FLOAT,

    -- Error info
    error_type VARCHAR(100),
    error_message TEXT,
    error_context JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_llm_logs_meeting ON llm_logs(meeting_id);
CREATE INDEX idx_llm_logs_created ON llm_logs(created_at);
CREATE INDEX idx_llm_logs_operation ON llm_logs(operation);
```

## 서비스 구현

### 파일: `app/services/processing_log.py`

```python
class ProcessingLogService:
    """STT/LLM 처리 로깅 서비스"""

    @staticmethod
    async def log_stt_start(session, recording_id, task_id, total_chunks, audio_duration):
        """STT 처리 시작 로그"""

    @staticmethod
    async def log_stt_chunk(session, recording_id, chunk_index, duration_seconds):
        """STT 청크 처리 완료 로그"""

    @staticmethod
    async def log_stt_complete(session, recording_id, task_id,
                                duration_seconds, transcript_length, word_count):
        """STT 처리 완료 로그"""

    @staticmethod
    async def log_stt_error(session, recording_id, task_id,
                            error_type, error_message, context):
        """STT 에러 로그"""

    @staticmethod
    async def log_llm_start(session, meeting_id, operation, provider, model, prompt_length):
        """LLM 호출 시작 로그"""

    @staticmethod
    async def log_llm_complete(session, meeting_id, operation,
                                duration_seconds, prompt_tokens, completion_tokens, cost):
        """LLM 호출 완료 로그"""

    @staticmethod
    async def log_llm_error(session, meeting_id, operation,
                            error_type, error_message, context):
        """LLM 에러 로그"""
```

## 수정할 파일

### 1. `backend/app/models/processing_log.py` (신규)

SQLAlchemy 모델 정의

### 2. `backend/alembic/versions/xxx_add_processing_logs.py` (신규)

마이그레이션 스크립트

### 3. `backend/app/services/processing_log.py` (신규)

로깅 서비스 구현

### 4. `backend/workers/tasks/stt.py` (수정)

- `process_stt` 시작 시 `log_stt_start()` 호출
- 청크 처리 완료 시 `log_stt_chunk()` 호출
- 전체 완료 시 `log_stt_complete()` 호출
- 에러 발생 시 `log_stt_error()` 호출

### 5. `backend/workers/tasks/llm.py` (수정)

- `generate_meeting_result` 시작 시 `log_llm_start()` 호출
- 완료 시 `log_llm_complete()` 호출
- 에러 발생 시 `log_llm_error()` 호출

### 6. `backend/app/services/llm.py` (수정)

- `generate_meeting_summary` 호출 전후 로깅
- `generate_questions` 호출 전후 로깅

## 구현 순서

1. 모델 생성 (`app/models/processing_log.py`)
2. 마이그레이션 생성 및 실행
3. 로깅 서비스 구현 (`app/services/processing_log.py`)
4. STT 태스크에 로깅 삽입 (`workers/tasks/stt.py`)
5. LLM 태스크/서비스에 로깅 삽입

## 비용 추정 공식

```python
# Gemini 1.5 Flash pricing (per 1M tokens)
GEMINI_INPUT_COST = 0.075   # $0.075 per 1M input tokens
GEMINI_OUTPUT_COST = 0.30   # $0.30 per 1M output tokens

def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens * GEMINI_INPUT_COST / 1_000_000) + \
           (completion_tokens * GEMINI_OUTPUT_COST / 1_000_000)
```

## 검증 쿼리

```sql
-- 일별 STT 처리 통계
SELECT DATE(created_at) as date,
       COUNT(*) as total_recordings,
       SUM(audio_duration_seconds) as total_audio_seconds,
       AVG(duration_seconds) as avg_processing_time
FROM stt_logs
WHERE event_type = 'complete'
GROUP BY DATE(created_at);

-- 일별 LLM 사용량
SELECT DATE(created_at) as date,
       operation,
       COUNT(*) as calls,
       SUM(prompt_tokens) as total_prompt_tokens,
       SUM(completion_tokens) as total_completion_tokens,
       SUM(estimated_cost_usd) as total_cost
FROM llm_logs
WHERE event_type = 'complete'
GROUP BY DATE(created_at), operation;

-- 에러 현황
SELECT event_type, error_type, COUNT(*) as count
FROM stt_logs WHERE error_type IS NOT NULL
GROUP BY event_type, error_type;
```

## 다음 단계

→ Do Phase: 위 설계대로 코드 구현
