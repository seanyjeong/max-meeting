# Database Schema

## 연결 정보

| 항목 | 값 |
|------|-----|
| **Engine** | PostgreSQL 16 |
| **Host** | localhost |
| **Port** | 5432 |
| **Database** | maxmeeting |
| **User** | maxmeeting |
| **Driver** | asyncpg |

## 테이블 (17개)

### meetings
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| type_id | INT FK | → meeting_types |
| title | VARCHAR(200) | |
| description | TEXT | |
| scheduled_at | TIMESTAMPTZ | |
| location | VARCHAR(200) | |
| status | VARCHAR(20) | draft/in_progress/completed |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | soft delete |

### meeting_types
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| name | VARCHAR(50) UNIQUE | |
| description | TEXT | |
| agenda_template | JSONB | |
| default_duration_minutes | INT | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | |

### meeting_attendees
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| meeting_id | INT FK | → meetings |
| contact_id | INT FK | → contacts |
| attended | BOOLEAN | |
| speaker_label | VARCHAR(50) | 화자 라벨 |
| created_at | TIMESTAMPTZ | |

### agendas
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| meeting_id | INT FK | → meetings |
| parent_id | INT FK | → agendas (self) |
| level | INT | 0=루트 |
| order_num | INT | |
| title | VARCHAR(200) | |
| description | TEXT | |
| duration_minutes | INT | |
| status | VARCHAR(20) | pending/in_progress/completed |
| started_at_seconds | INT | 녹음 시작 위치 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | |

### agenda_questions
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| agenda_id | INT FK | → agendas |
| order_num | INT | |
| question | TEXT | 질문 내용 |
| is_generated | BOOLEAN | LLM 생성 여부 (true=LLM, false=수동) |
| answered | BOOLEAN | 답변 완료 여부 |
| created_at | TIMESTAMPTZ | |

### contacts
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| name | VARCHAR(100) | |
| role | VARCHAR(100) | |
| organization | VARCHAR(100) | |
| position | VARCHAR(50) | |
| phone_encrypted | BYTEA | PII 암호화 |
| email_encrypted | BYTEA | PII 암호화 |
| notes | TEXT | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | |

### recordings
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| meeting_id | INT FK | → meetings |
| file_path | VARCHAR(500) | |
| original_filename | VARCHAR(200) | 원본 파일명 |
| safe_filename | VARCHAR(200) | 안전한 파일명 |
| mime_type | VARCHAR(50) | audio/webm 등 |
| duration_seconds | INT | |
| file_size_bytes | BIGINT | |
| format | VARCHAR(20) | webm/mp3 |
| checksum | VARCHAR(64) | 파일 체크섬 |
| status | VARCHAR(20) | uploaded/processing/completed/failed |
| error_message | TEXT | |
| retry_count | INT | 재시도 횟수 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### transcripts
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| recording_id | INT FK | → recordings |
| meeting_id | INT FK | → meetings |
| chunk_index | INT | 청크 인덱스 |
| segments | JSONB | 타임스탬프별 세그먼트 |
| full_text | TEXT | 전체 텍스트 (레거시) |
| language | VARCHAR(10) | |
| confidence_avg | FLOAT | |
| created_at | TIMESTAMPTZ | |

### meeting_results
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| meeting_id | INT FK | → meetings |
| version | INT | 버전 관리 |
| summary | TEXT | |
| key_points | JSONB | |
| generated_by | VARCHAR(50) | llm/manual |
| is_final | BOOLEAN | |
| is_verified | BOOLEAN | 검증 완료 여부 |
| verified_at | TIMESTAMPTZ | 검증 시간 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### meeting_decisions
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| meeting_id | INT FK | → meetings |
| agenda_id | INT FK | → agendas |
| decision_type | VARCHAR | approved/postponed/rejected |
| content | TEXT | |
| created_at | TIMESTAMPTZ | |

### agenda_discussions
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| agenda_id | INT FK | → agendas |
| content | TEXT | 토론 내용 |
| is_llm_generated | BOOLEAN | LLM 생성 여부 |
| version | INT | 버전 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### action_items
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| result_id | INT FK (nullable) | → meeting_results |
| meeting_id | INT FK | → meetings |
| agenda_id | INT FK | → agendas |
| assignee_id | INT FK | → contacts |
| title | VARCHAR(200) | |
| content | TEXT | |
| description | TEXT | |
| due_date | DATE | |
| priority | VARCHAR(20) | high/medium/low |
| status | VARCHAR(20) | pending/in_progress/completed |
| completed_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### manual_notes
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| meeting_id | INT FK | → meetings |
| agenda_id | INT FK | → agendas |
| content | TEXT | |
| timestamp_seconds | INT | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### sketches
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| meeting_id | INT FK | → meetings |
| agenda_id | INT FK | → agendas |
| json_data | JSONB | tldraw 데이터 |
| svg_file_path | VARCHAR(500) | SVG 파일 경로 |
| extracted_text | TEXT | OCR 추출 텍스트 |
| thumbnail_path | VARCHAR(500) | |
| timestamp_seconds | INT | 녹음 시간 위치 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### task_trackings
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| recording_id | INT FK | → recordings |
| meeting_id | INT FK | → meetings |
| task_id | VARCHAR | Celery task ID |
| task_type | VARCHAR | stt/llm |
| status | VARCHAR | pending/processing/completed/failed |
| progress | INT | 0-100 |
| result | JSONB | |
| error_message | TEXT | |
| started_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

### audit_logs
| Column | Type | 설명 |
|--------|------|------|
| id | SERIAL PK | |
| timestamp | TIMESTAMPTZ | |
| user_id | VARCHAR | |
| ip_address | INET | |
| request_id | UUID | |
| event | VARCHAR | |
| resource_type | VARCHAR | |
| resource_id | VARCHAR | |
| action | VARCHAR | CREATE/READ/UPDATE/DELETE |
| status | VARCHAR | SUCCESS/FAILURE |
| details | JSONB | |

## 인덱스

- **pg_trgm**: contacts.name, meeting_results.summary
- **Composite**: meetings(type_id, status), meetings(scheduled_at DESC)
- **FK indexes**: 모든 외래키 컬럼
- **transcripts**: idx_transcripts_meeting(meeting_id), idx_transcripts_recording(recording_id, chunk_index)

## 관계도

```
meeting_types 1──N meetings 1──N agendas 1──N agenda_questions
                      │              │
                      │              └──N manual_notes
                      │              └──N sketches
                      │              └──N agenda_discussions
                      │              └──N meeting_decisions
                      │              └──N action_items
                      │
                      ├──N meeting_attendees N──1 contacts
                      ├──N recordings 1──N transcripts
                      ├──N meeting_results
                      └──N task_trackings
```

## 마이그레이션 히스토리

| 버전 | 설명 |
|------|------|
| c27eaefe701b | 초기 스키마 |
| e3b64dac2684 | pg_trgm 검색 인덱스 추가 |
| 1683beaa9622 | 안건 계층 구조 추가 |
| fix_schema_mismatch_001 | DB-모델 컬럼 매칭 수정 |
