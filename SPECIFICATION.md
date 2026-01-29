다# MAX Meeting - 프로젝트 명세서

> 회의 관리 SaaS - 안건 등록부터 자동 정리까지

**Version:** 1.0.2
**Last Updated:** 2026-01-29
**Author:** ET (@etlab.kr)

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [백엔드 API 명세](#3-백엔드-api-명세)
4. [데이터베이스 스키마](#4-데이터베이스-스키마)
5. [프론트엔드 구조](#5-프론트엔드-구조)
6. [비즈니스 로직](#6-비즈니스-로직)
7. [인증 및 보안](#7-인증-및-보안)
8. [설정 및 환경변수](#8-설정-및-환경변수)
9. [배포 가이드](#9-배포-가이드)

---

## 1. 프로젝트 개요

### 1.1 목적

MAX Meeting은 회의 전체 워크플로우를 하나의 웹 애플리케이션에서 처리하는 통합 솔루션입니다:

- **회의 전**: 안건 등록 → LLM이 질문지 자동 생성
- **회의 중**: 녹음 + 펜슬 필기 (tldraw) + 타이핑 메모
- **회의 후**: STT → LLM 회의록 자동 생성 → 사용자 검증 → 저장

### 1.2 핵심 기능

| 기능 영역 | 세부 기능 |
|---------|---------|
| **회의 관리** | 회의 생성/수정/삭제(소프트), 회의 유형 관리, 참석자 관리, 상태 추적 |
| **안건 관리** | 안건 CRUD, 순서 변경, LLM 질문 자동 생성, **계층 구조 인식** 텍스트 파싱으로 일괄 생성 |
| **녹음** | 브라우저 녹음, 실시간 파형, 배터리 경고, Wake Lock, IndexedDB 자동 저장 |
| **필기** | tldraw 펜슬 필기, React-Svelte 브릿지, JSONB 저장 |
| **STT** | faster-whisper (CPU int8), pyannote 화자분리, 청크 병렬 처리 |
| **회의록** | Gemini Flash 자동 요약, 수동 편집, 버전 관리, 결정사항/액션아이템 추출 |
| **회의 인사이트** | **회의 분위기 분석** (긍정/중립/긴장), **합의 수준** (0-100), **핵심 전환점** 추출, **주요 기여자** 식별, **미해결 이슈** 감지 |
| **발언자 분석** | 발언 시간, 참여도 점수, 감정 분석, 질문/진술 비율, 주요 키워드 추출 |
| **검색** | pg_trgm 전문 검색 (회의록, 연락처, 전사록) |
| **오프라인** | PWA, 오프라인 캐시, 동기화, 충돌 해결 |

### 1.3 기술 스택

#### 백엔드

| 구분 | 기술 | 버전 |
|-----|------|------|
| **언어** | Python | 3.11 |
| **프레임워크** | FastAPI | 0.109.0 |
| **ORM** | SQLAlchemy (비동기) | 2.0.25 |
| **DB 드라이버** | asyncpg | 0.29.0 |
| **인증** | python-jose, passlib | 3.3.0, 1.7.4 |
| **작업 큐** | Celery, Redis | 5.3.6, 5.0.1 |
| **STT** | faster-whisper, pyannote.audio | 1.0.0+, 3.1.1 |
| **LLM** | google-generativeai | 0.3.2 |
| **모니터링** | Sentry | 1.40.0 |

#### 프론트엔드

| 구분 | 기술 | 버전 |
|-----|------|------|
| **언어** | TypeScript | 5.0 |
| **프레임워크** | SvelteKit 5 + Svelte 5 (Runes) | 5.0.0 |
| **스타일링** | TailwindCSS | 3.4.0 |
| **필기 도구** | tldraw v4 (React 브릿지) | 4.3.0 |
| **빌드 도구** | Vite | 5.4.0 |
| **테스트** | Vitest | 2.0.0 |

#### 인프라

| 구분 | 기술 | 버전 |
|-----|------|------|
| **데이터베이스** | PostgreSQL (pg_trgm, pgcrypto) | 16 |
| **캐시/큐** | Redis | 7 |
| **컨테이너** | Docker, Docker Compose | - |
| **서버** | uvicorn, Node.js | 0.27.0, 20+ |

---

## 2. 시스템 아키텍처

### 2.1 전체 구조 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client (Browser)                            │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ SvelteKit UI │  │  IndexedDB   │  │ Service      │              │
│  │ (Svelte 5)   │  │  (Offline)   │  │ Worker (PWA) │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                  │                       │
└─────────┼──────────────────┼──────────────────┼───────────────────────┘
          │                  │                  │
          │ HTTP/REST        │ Sync             │ Cache
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼───────────────────────┐
│                       Reverse Proxy (Caddy)                           │
└─────────┬──────────────────────────────────────────────────────────┬─┘
          │                                                          │
          │                                                          │
┌─────────▼────────────────────────┐              ┌─────────────────▼───┐
│    FastAPI Backend (uvicorn)     │              │  Frontend (Node.js) │
│                                  │              │                     │
│  ┌────────────────────────────┐ │              │  Build output:      │
│  │  API Routers (10개)        │ │              │  /build/            │
│  │  - auth, meetings, agendas │ │              └─────────────────────┘
│  │  - contacts, recordings    │ │
│  │  - results, search, etc.   │ │
│  └────────┬───────────────────┘ │
│           │                      │
│  ┌────────▼───────────────────┐ │
│  │  Services (비즈니스 로직)   │ │
│  │  - MeetingService          │ │
│  │  - RecordingService        │ │
│  │  - ResultService           │ │
│  │  - SearchService           │ │
│  │  - SpeakerAnalyticsService │ │
│  │    (발언자 분석 - 감정, 참여도)│ │
│  └────────┬───────────────────┘ │
│           │                      │
│  ┌────────▼───────────────────┐ │
│  │  SQLAlchemy ORM (async)    │ │
│  └────────┬───────────────────┘ │
└───────────┼──────────────────────┘
            │
            │ asyncpg
            │
┌───────────▼──────────────────────┐       ┌────────────────────────────┐
│    PostgreSQL 16                 │       │       Redis 7              │
│                                  │       │                            │
│  - 15개 테이블                   │       │  - Rate limiting          │
│  - pg_trgm (전문검색)            │◄──────┤  - Celery broker          │
│  - pgcrypto (PII 암호화)         │       │  - STT progress (SSE)     │
└──────────────────────────────────┘       └────────────────────────────┘
            ▲                                         ▲
            │                                         │
            │                                         │
┌───────────▼─────────────────────────────────────────▼───────────────┐
│                    Celery Worker (백그라운드 작업)                  │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  STT Task        │  │  LLM Task        │  │  Cleanup Task    │ │
│  │  (faster-whisper)│  │  (Gemini Flash)  │  │                  │ │
│  │  (pyannote)      │  │                  │  │                  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 데이터 흐름

#### 2.2.1 회의 생성 흐름

```
User → Frontend → POST /api/v1/meetings
                 → MeetingService.create()
                 → SQLAlchemy → PostgreSQL (meetings 테이블)
                 → Response: MeetingDetailResponse
```

#### 2.2.2 녹음 업로드 및 STT 흐름

```
Browser Recording → IndexedDB 자동 저장 (5분마다)
                  → POST /api/v1/meetings/{id}/recordings (초기화)
                  → POST /api/v1/recordings/{id}/upload (청크 업로드)
                  → RecordingService.init_upload()
                  → File: /data/max-meeting/recordings/{safe_filename}
                  → Celery Task: stt_task.delay(recording_id)
                  → faster-whisper (CPU, int8, medium 모델)
                  → pyannote.audio (화자분리)
                  → Transcript 저장 (JSONB segments)
                  → Redis Pub/Sub (SSE progress)
                  → Frontend: GET /api/v1/recordings/{id}/progress (SSE)
```

#### 2.2.3 회의록 생성 흐름

```
Transcripts (JSONB) → Celery Task: generate_meeting_result.delay()
                    → Gemini Flash API
                    → 요약, 결정사항, 액션아이템 추출
                    → MeetingResult, MeetingDecision, ActionItem 저장
                    → Frontend: GET /api/v1/results/{id}
                    → SummaryEditor 컴포넌트로 수동 편집
                    → PATCH /api/v1/results/{id}
                    → POST /api/v1/results/{id}/verify (검증 완료)
```

### 2.3 주요 컴포넌트 관계

```
┌────────────────────────────────────────────────────────────────────┐
│                        Frontend Components                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Routes (12개)                    Components (26개)                │
│  ┌──────────────────┐             ┌──────────────────┐            │
│  │ /                │             │ RecordButton     │            │
│  │ /login           │             │ Waveform         │            │
│  │ /meetings        │◄────────────┤ AgendaTracker    │            │
│  │ /meetings/new    │             │ TldrawWrapper    │            │
│  │ /meetings/{id}   │             │ TranscriptViewer │            │
│  │ /meetings/{id}/  │             │ SummaryEditor    │            │
│  │   record         │             │ ActionItems      │            │
│  │ /meetings/{id}/  │             └──────────────────┘            │
│  │   sketch         │                                              │
│  │ /meetings/{id}/  │             Stores (8개)                    │
│  │   results        │             ┌──────────────────┐            │
│  │ /meetings/{id}/  │◄────────────┤ auth.ts          │            │
│  │   results/edit   │             │ meeting.ts       │            │
│  │ /meetings/deleted│             │ recording.ts     │            │
│  │ /contacts        │             │ results.ts       │            │
│  │ /contacts/new    │             │ sketch.ts        │            │
│  │ /contacts/{id}   │             │ contacts.ts      │            │
│  └──────────────────┘             │ offline.ts       │            │
│                                    │ toast.ts         │            │
│                                    └──────────────────┘            │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. 백엔드 API 명세

### 3.1 API 엔드포인트 개요

**Base URL:** `/api/v1`

총 **47개** 엔드포인트, 10개 라우터로 구성

### 3.2 인증 (Authentication)

**Router:** `/auth`

| Method | Endpoint | 설명 | Rate Limit |
|--------|----------|------|------------|
| POST | `/auth/login` | 비밀번호 로그인, JWT 토큰 발급 | 5/minute |
| POST | `/auth/refresh` | Refresh token으로 새 토큰 발급 | 10/minute |
| POST | `/auth/logout` | 로그아웃 (클라이언트 토큰 삭제) | - |
| GET | `/auth/me` | 현재 사용자 정보 조회 | - |

**Request Example (Login):**

```json
POST /api/v1/auth/login
{
  "password": "your-password"
}
```

**Response Example (Login):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3.3 회의 (Meetings)

**Router:** `/meetings`

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/meetings` | 회의 목록 조회 (필터: status, type_id, from, to, deleted_only) |
| GET | `/meetings/{id}` | 회의 상세 조회 (참석자, 안건 포함) |
| POST | `/meetings` | 새 회의 생성 |
| PATCH | `/meetings/{id}` | 회의 수정 |
| DELETE | `/meetings/{id}` | 회의 소프트 삭제 |
| POST | `/meetings/{id}/restore` | 삭제된 회의 복원 |
| POST | `/meetings/{id}/attendees` | 참석자 추가 |
| DELETE | `/meetings/{id}/attendees/{contact_id}` | 참석자 제거 |

**Request Example (Create Meeting):**

```json
POST /api/v1/meetings
{
  "title": "2026년 1월 주간 회의",
  "type_id": 1,
  "scheduled_at": "2026-01-30T14:00:00+09:00",
  "location": "본사 3층 회의실",
  "attendee_ids": [1, 2, 3]
}
```

**Response Example (Meeting Detail):**

```json
{
  "id": 1,
  "title": "2026년 1월 주간 회의",
  "type_id": 1,
  "meeting_type": {
    "id": 1,
    "name": "주간회의"
  },
  "scheduled_at": "2026-01-30T14:00:00+09:00",
  "location": "본사 3층 회의실",
  "status": "draft",
  "created_at": "2026-01-29T10:00:00+09:00",
  "updated_at": "2026-01-29T10:00:00+09:00",
  "attendees": [
    {
      "id": 1,
      "contact_id": 1,
      "attended": false,
      "speaker_label": "Speaker 0",
      "contact": {
        "id": 1,
        "name": "홍길동",
        "organization": "ABC주식회사",
        "role": "팀장"
      }
    }
  ],
  "agendas": [
    {
      "id": 1,
      "order_num": 0,
      "title": "프로젝트 진행 현황",
      "status": "pending",
      "started_at_seconds": null
    }
  ]
}
```

### 3.4 안건 (Agendas)

**Router:** `/agendas` (일부는 `/meetings/{id}/agendas`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/meetings/{id}/agendas` | 회의의 안건 목록 조회 |
| POST | `/meetings/{id}/agendas` | 안건 생성 (자동 질문 생성) |
| POST | `/meetings/{id}/agendas/parse` | 텍스트 파싱으로 다중 안건 생성 (LLM) |
| POST | `/agendas/parse-preview` | 안건 파싱 미리보기 (저장 안 함) |
| GET | `/agendas/{id}` | 안건 상세 조회 |
| PATCH | `/agendas/{id}` | 안건 수정 |
| DELETE | `/agendas/{id}` | 안건 소프트 삭제 |
| POST | `/agendas/{id}/reorder` | 안건 순서 변경 |
| POST | `/agendas/{id}/questions` | 질문 추가 |
| PATCH | `/questions/{id}` | 질문 수정 |
| DELETE | `/questions/{id}` | 질문 삭제 |

**Request Example (Parse Agendas - 계층 구조 지원):**

```json
POST /api/v1/meetings/1/agendas/parse
{
  "text": "1. 예산안 심의\n   - 2024년 예산 검토\n   - 비용 절감 방안\n2. 인사 발표\n   - 신규 채용 현황\n3. 기타 안건"
}
```

**Response Example (계층 구조 파싱 결과):**

```json
{
  "data": [
    {
      "id": 1,
      "title": "예산안 심의",
      "description": "- 2024년 예산 검토\n- 비용 절감 방안"
    },
    {
      "id": 2,
      "title": "인사 발표",
      "description": "- 신규 채용 현황"
    },
    {
      "id": 3,
      "title": "기타 안건",
      "description": ""
    }
  ],
  "meta": {"total": 3, "source": "llm_parsed"}
}
```

> **참고:** LLM이 계층 구조를 자동 인식합니다. 번호가 붙은 항목(1., 2. 등)은 메인 안건으로, 들여쓰기된 하위 항목(-, *, 탭 등)은 해당 안건의 `description` 필드에 병합됩니다.

**Response Example (Agenda with Questions):**

```json
{
  "id": 1,
  "meeting_id": 1,
  "order_num": 0,
  "title": "프로젝트 진행 현황",
  "description": "1분기 프로젝트 진행 상황 점검",
  "status": "pending",
  "started_at_seconds": null,
  "questions": [
    {
      "id": 1,
      "question": "현재 프로젝트 완료율은 얼마입니까?",
      "order_num": 0,
      "is_generated": true,
      "answered": false
    }
  ]
}
```

### 3.5 녹음 (Recordings)

**Router:** `/recordings` (일부는 `/meetings/{id}/recordings`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/meetings/{id}/recordings` | 녹음 초기화 (메타데이터 생성) |
| GET | `/recordings/{id}` | 녹음 상세 조회 (전사록 포함) |
| PATCH | `/recordings/{id}` | 녹음 상태 수정 |
| DELETE | `/recordings/{id}` | 녹음 삭제 (파일 포함) |
| POST | `/recordings/{id}/upload` | 청크 업로드 (TUS-like) |
| HEAD | `/recordings/{id}/upload` | 업로드 진행 상태 조회 |
| GET | `/recordings/{id}/progress` | STT 진행 상황 스트리밍 (SSE) |

**Request Example (Init Upload):**

```json
POST /api/v1/meetings/1/recordings
{
  "original_filename": "meeting_2026-01-30.webm",
  "mime_type": "audio/webm",
  "format": "webm",
  "duration_seconds": 3600,
  "checksum": "abc123def456..."
}
```

**Response Example (Upload Progress - SSE):**

```
event: connected
data: {"recording_id": 1}

event: progress
data: {"status": "processing", "progress": 25, "message": "청크 1/4 처리 중..."}

event: progress
data: {"status": "completed", "progress": 100, "message": "STT 완료"}
```

### 3.6 회의록 (Results)

**Router:** `/results` (일부는 `/meetings/{id}/results`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/meetings/{id}/results` | 회의록 버전 목록 조회 |
| POST | `/meetings/{id}/results` | 새 회의록 버전 생성 |
| GET | `/results/{id}` | 회의록 상세 조회 (결정사항, 액션아이템 포함) |
| PATCH | `/results/{id}` | 회의록 수정 |
| POST | `/results/{id}/verify` | 회의록 검증 완료 |
| POST | `/results/{id}/regenerate` | LLM 재생성 트리거 |
| GET | `/meetings/{id}/action-items` | 액션아이템 목록 조회 |
| POST | `/results/{id}/action-items` | 액션아이템 추가 |
| PATCH | `/action-items/{id}` | 액션아이템 수정 |
| DELETE | `/action-items/{id}` | 액션아이템 삭제 |

**Response Example (Result Detail):**

```json
{
  "id": 1,
  "meeting_id": 1,
  "summary": "2026년 1월 주간 회의 요약...",
  "is_verified": true,
  "verified_at": "2026-01-30T16:00:00+09:00",
  "version": 1,
  "decisions": [
    {
      "id": 1,
      "content": "예산을 10% 증액하기로 결정",
      "decision_type": "approved"
    }
  ],
  "action_items": [
    {
      "id": 1,
      "content": "프로젝트 계획서 수정",
      "assignee_id": 1,
      "assignee": {
        "id": 1,
        "name": "홍길동"
      },
      "due_date": "2026-02-05",
      "priority": "high",
      "status": "pending"
    }
  ]
}
```

### 3.7 연락처 (Contacts)

**Router:** `/contacts`

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/contacts` | 연락처 목록 조회 (검색: q, 페이징: limit/offset) |
| GET | `/contacts/{id}` | 연락처 상세 조회 |
| POST | `/contacts` | 연락처 생성 (PII 자동 암호화) |
| PATCH | `/contacts/{id}` | 연락처 수정 |
| DELETE | `/contacts/{id}` | 연락처 소프트 삭제 |

**Response Example (Contact):**

```json
{
  "id": 1,
  "name": "홍길동",
  "role": "팀장",
  "organization": "ABC주식회사",
  "phone": "010-1234-5678",  // 자동 복호화
  "email": "hong@example.com"  // 자동 복호화
}
```

### 3.8 검색 (Search)

**Router:** `/search`

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/search?q={query}` | 전체 검색 (회의록, 연락처, 전사록) |

**Response Example (Search Results):**

```json
{
  "data": {
    "meetings": [
      {
        "id": 1,
        "title": "2026년 1월 주간 회의",
        "snippet": "...프로젝트 진행 현황...",
        "score": 0.95
      }
    ],
    "contacts": [
      {
        "id": 1,
        "name": "홍길동",
        "snippet": "...팀장...",
        "score": 0.87
      }
    ],
    "transcripts": [
      {
        "id": 1,
        "meeting_id": 1,
        "snippet": "...예산 증액...",
        "score": 0.78
      }
    ]
  },
  "meta": {
    "query": "프로젝트",
    "total": 3,
    "limit": 20,
    "offset": 0
  }
}
```

### 3.9 회의 유형 (Meeting Types)

**Router:** `/meeting-types`

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/meeting-types` | 회의 유형 목록 조회 |
| POST | `/meeting-types` | 회의 유형 생성 |
| PATCH | `/meeting-types/{id}` | 회의 유형 수정 |
| DELETE | `/meeting-types/{id}` | 회의 유형 소프트 삭제 |

### 3.10 필기 (Sketches)

**Router:** `/sketches` (일부는 `/meetings/{id}/sketches`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/meetings/{id}/sketches` | 회의의 필기 목록 조회 |
| POST | `/meetings/{id}/sketches` | 필기 저장 (tldraw JSONB) |
| GET | `/sketches/{id}` | 필기 상세 조회 |
| PATCH | `/sketches/{id}` | 필기 수정 |
| DELETE | `/sketches/{id}` | 필기 삭제 |

### 3.11 메모 (Notes)

**Router:** `/notes` (일부는 `/meetings/{id}/notes`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/meetings/{id}/notes` | 회의의 메모 목록 조회 |
| POST | `/meetings/{id}/notes` | 메모 생성 |
| PATCH | `/notes/{id}` | 메모 수정 |
| DELETE | `/notes/{id}` | 메모 삭제 |

### 3.12 헬스체크

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/health` | API 서버 상태 확인 |

---

## 4. 데이터베이스 스키마

### 4.1 테이블 목록 (총 16개)

| 순번 | 테이블명 | 설명 | 주요 컬럼 |
|-----|---------|------|----------|
| 1 | `meeting_types` | 회의 유형 | id, name |
| 2 | `meetings` | 회의 | id, type_id, title, scheduled_at, status |
| 3 | `meeting_attendees` | 회의 참석자 (N:N) | id, meeting_id, contact_id, attended |
| 4 | `contacts` | 연락처 | id, name, phone_encrypted, email_encrypted |
| 5 | `agendas` | 안건 | id, meeting_id, order_num, title, status |
| 6 | `agenda_questions` | 안건 질문 | id, agenda_id, question, is_generated |
| 7 | `recordings` | 녹음 파일 | id, meeting_id, file_path, status, checksum |
| 8 | `transcripts` | STT 전사록 | id, recording_id, chunk_index, segments (JSONB) |
| 9 | `manual_notes` | 타이핑 메모 | id, meeting_id, agenda_id, content |
| 10 | `sketches` | 펜슬 필기 | id, meeting_id, agenda_id, tldraw_data (JSONB) |
| 11 | `meeting_results` | 회의록 | id, meeting_id, summary, version, is_verified |
| 12 | `meeting_decisions` | 결정사항 | id, meeting_id, agenda_id, content, decision_type |
| 13 | `agenda_discussions` | 안건 토론 내용 | id, agenda_id, content, version |
| 14 | `action_items` | 액션아이템 | id, meeting_id, assignee_id, content, due_date, status |
| 15 | `task_tracking` | Celery 작업 추적 | id, meeting_id, task_id, task_type, status |
| 16 | `audit_logs` | 감사 로그 | id, action, entity_type, entity_id, user_id |

### 4.2 상세 스키마

#### 4.2.1 meeting_types

```sql
CREATE TABLE meeting_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_meeting_types_name ON meeting_types(name) WHERE deleted_at IS NULL;
```

#### 4.2.2 meetings

```sql
CREATE TYPE meeting_status AS ENUM ('draft', 'in_progress', 'completed');

CREATE TABLE meetings (
    id SERIAL PRIMARY KEY,
    type_id INTEGER REFERENCES meeting_types(id),
    title VARCHAR(200) NOT NULL,
    scheduled_at TIMESTAMP,
    location VARCHAR(200),
    status meeting_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_meetings_type_status ON meetings(type_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_meetings_scheduled ON meetings(scheduled_at DESC) WHERE deleted_at IS NULL;
```

#### 4.2.3 meeting_attendees

```sql
CREATE TABLE meeting_attendees (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES contacts(id),
    attended BOOLEAN NOT NULL DEFAULT FALSE,
    speaker_label VARCHAR(50),
    CONSTRAINT uq_meeting_contact UNIQUE (meeting_id, contact_id)
);

CREATE INDEX idx_meeting_attendees_meeting ON meeting_attendees(meeting_id);
CREATE INDEX idx_meeting_attendees_contact ON meeting_attendees(contact_id);
```

#### 4.2.4 contacts (PII 암호화)

```sql
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50),
    organization VARCHAR(100),
    phone_encrypted BYTEA,  -- pgcrypto 암호화
    email_encrypted BYTEA,  -- pgcrypto 암호화
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

-- pg_trgm 인덱스 (퍼지 검색)
CREATE INDEX idx_contacts_name ON contacts(name) WHERE deleted_at IS NULL;
CREATE INDEX idx_contacts_name_trgm ON contacts USING GIN (name gin_trgm_ops);
```

#### 4.2.5 agendas

```sql
CREATE TYPE agenda_status AS ENUM ('pending', 'in_progress', 'completed', 'skipped');

CREATE TABLE agendas (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    order_num INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status agenda_status NOT NULL DEFAULT 'pending',
    started_at_seconds INTEGER,  -- 녹음 내 시작 시각
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_agendas_meeting_order ON agendas(meeting_id, order_num);
```

#### 4.2.6 agenda_questions

```sql
CREATE TABLE agenda_questions (
    id SERIAL PRIMARY KEY,
    agenda_id INTEGER NOT NULL REFERENCES agendas(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    order_num INTEGER NOT NULL,
    is_generated BOOLEAN NOT NULL DEFAULT TRUE,
    answered BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_agenda_questions_agenda ON agenda_questions(agenda_id);
```

#### 4.2.7 recordings

```sql
CREATE TYPE recording_status AS ENUM ('uploaded', 'processing', 'completed', 'failed');

CREATE TABLE recordings (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    original_filename VARCHAR(200),
    safe_filename VARCHAR(100) NOT NULL,
    mime_type VARCHAR(50) NOT NULL,
    format VARCHAR(20) NOT NULL DEFAULT 'webm',
    duration_seconds INTEGER,
    file_size_bytes BIGINT,
    checksum VARCHAR(64) NOT NULL,
    status recording_status NOT NULL DEFAULT 'uploaded',
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recordings_meeting ON recordings(meeting_id);
```

#### 4.2.8 transcripts

```sql
CREATE TABLE transcripts (
    id SERIAL PRIMARY KEY,
    recording_id INTEGER NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    segments JSONB NOT NULL,  -- [{start, end, text, speaker}]
    -- transcript_text는 generated column (PostgreSQL)
    -- GENERATED ALWAYS AS (jsonb_array_to_text(segments)) STORED
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transcripts_recording ON transcripts(recording_id, chunk_index);
CREATE INDEX idx_transcripts_meeting ON transcripts(meeting_id);

-- pg_trgm 인덱스 (전문 검색)
-- transcript_text 컬럼에 대해 마이그레이션에서 생성
-- CREATE INDEX idx_transcripts_text_trgm ON transcripts USING GIN (transcript_text gin_trgm_ops);
```

#### 4.2.9 manual_notes

```sql
CREATE TABLE manual_notes (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agenda_id INTEGER REFERENCES agendas(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_manual_notes_meeting ON manual_notes(meeting_id);
```

#### 4.2.10 sketches

```sql
CREATE TABLE sketches (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agenda_id INTEGER REFERENCES agendas(id),
    tldraw_data JSONB NOT NULL,  -- tldraw snapshot
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sketches_meeting ON sketches(meeting_id);
```

#### 4.2.11 meeting_results

```sql
CREATE TABLE meeting_results (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    summary TEXT,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_meeting_result_version UNIQUE (meeting_id, version)
);

-- pg_trgm 인덱스 (전문 검색)
CREATE INDEX idx_meeting_results_summary_trgm ON meeting_results USING GIN (summary gin_trgm_ops);
```

#### 4.2.12 meeting_decisions

```sql
CREATE TYPE decision_type AS ENUM ('approved', 'rejected', 'deferred', 'info_only');

CREATE TABLE meeting_decisions (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agenda_id INTEGER REFERENCES agendas(id),
    content TEXT NOT NULL,
    decision_type decision_type NOT NULL DEFAULT 'approved',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_meeting_decisions_meeting ON meeting_decisions(meeting_id);
```

#### 4.2.13 agenda_discussions

```sql
CREATE TABLE agenda_discussions (
    id SERIAL PRIMARY KEY,
    agenda_id INTEGER NOT NULL REFERENCES agendas(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_llm_generated BOOLEAN NOT NULL DEFAULT TRUE,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agenda_discussions_agenda ON agenda_discussions(agenda_id);
```

#### 4.2.14 action_items

```sql
CREATE TYPE action_item_status AS ENUM ('pending', 'in_progress', 'completed', 'cancelled');
CREATE TYPE action_item_priority AS ENUM ('low', 'medium', 'high', 'urgent');

CREATE TABLE action_items (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agenda_id INTEGER REFERENCES agendas(id),
    assignee_id INTEGER REFERENCES contacts(id),
    content TEXT NOT NULL,
    due_date DATE,
    priority action_item_priority NOT NULL DEFAULT 'medium',
    status action_item_status NOT NULL DEFAULT 'pending',
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_action_items_meeting ON action_items(meeting_id, status);
CREATE INDEX idx_action_items_assignee ON action_items(assignee_id, due_date);
```

#### 4.2.15 task_tracking

```sql
CREATE TYPE task_status AS ENUM ('pending', 'processing', 'completed', 'failed');

CREATE TABLE task_tracking (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id),
    recording_id INTEGER REFERENCES recordings(id),
    task_id VARCHAR(100) NOT NULL UNIQUE,  -- Celery task ID
    task_type VARCHAR(50) NOT NULL,  -- 'stt', 'llm', 'cleanup'
    status task_status NOT NULL DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_tracking_task_id ON task_tracking(task_id);
CREATE INDEX idx_task_tracking_meeting ON task_tracking(meeting_id);
```

#### 4.2.16 audit_logs

```sql
CREATE TYPE audit_action AS ENUM ('create', 'update', 'delete', 'restore', 'verify');

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    action audit_action NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    user_id VARCHAR(50),
    changes JSONB,  -- 변경 내용
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
```

### 4.3 관계 (Foreign Keys)

```
meeting_types
  └─ meetings (type_id)
       ├─ meeting_attendees (meeting_id)
       │    └─ contacts (contact_id)
       ├─ agendas (meeting_id)
       │    ├─ agenda_questions (agenda_id)
       │    ├─ agenda_discussions (agenda_id)
       │    ├─ manual_notes (agenda_id)
       │    ├─ sketches (agenda_id)
       │    ├─ meeting_decisions (agenda_id)
       │    └─ action_items (agenda_id)
       ├─ recordings (meeting_id)
       │    ├─ transcripts (recording_id)
       │    └─ task_tracking (recording_id)
       ├─ manual_notes (meeting_id)
       ├─ sketches (meeting_id)
       ├─ meeting_results (meeting_id)
       ├─ meeting_decisions (meeting_id)
       ├─ action_items (meeting_id)
       └─ task_tracking (meeting_id)

contacts
  ├─ meeting_attendees (contact_id)
  └─ action_items (assignee_id)
```

---

## 5. 프론트엔드 구조

### 5.1 페이지 라우트 (13개)

| 경로 | 파일 | 설명 |
|------|------|------|
| `/` | `/routes/+page.svelte` | 대시보드 (회의 목록) |
| `/login` | `/routes/login/+page.svelte` | 로그인 페이지 |
| `/meetings` | `/routes/meetings/+page.svelte` | 회의 목록 |
| `/meetings/new` | `/routes/meetings/new/+page.svelte` | 새 회의 생성 |
| `/meetings/deleted` | `/routes/meetings/deleted/+page.svelte` | 삭제된 회의 목록 |
| `/meetings/{id}` | `/routes/meetings/[id]/+page.svelte` | 회의 상세 (안건 관리) |
| `/meetings/{id}/record` | `/routes/meetings/[id]/record/+page.svelte` | 녹음 페이지 |
| `/meetings/{id}/sketch` | `/routes/meetings/[id]/sketch/+page.svelte` | 필기 페이지 (tldraw) |
| `/meetings/{id}/results` | `/routes/meetings/[id]/results/+page.svelte` | 회의록 조회 |
| `/meetings/{id}/results/edit` | `/routes/meetings/[id]/results/edit/+page.svelte` | 회의록 편집 |
| `/contacts` | `/routes/contacts/+page.svelte` | 연락처 목록 |
| `/contacts/new` | `/routes/contacts/new/+page.svelte` | 새 연락처 생성 |
| `/contacts/{id}` | `/routes/contacts/[id]/+page.svelte` | 연락처 상세/수정 |

### 5.2 컴포넌트 목록 (26개)

#### 5.2.1 공통 컴포넌트

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| Card | `Card.svelte` | 카드 레이아웃 |
| Button | `Button.svelte` | 버튼 (primary, secondary, danger) |
| Input | `Input.svelte` | 입력 필드 |
| Modal | `Modal.svelte` | 모달 다이얼로그 |
| Badge | `Badge.svelte` | 상태 뱃지 |
| Toast | `Toast.svelte` | 토스트 알림 (단일) |
| ToastContainer | `ToastContainer.svelte` | 토스트 컨테이너 |
| LoadingSpinner | `LoadingSpinner.svelte` | 로딩 스피너 |
| Breadcrumb | `Breadcrumb.svelte` | 브레드크럼 네비게이션 |
| SkipLink | `SkipLink.svelte` | 접근성: 본문 바로가기 |

#### 5.2.2 녹음 관련

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| RecordButton | `recording/RecordButton.svelte` | 녹음 시작/중지 버튼 |
| RecordingGuard | `recording/RecordingGuard.svelte` | 녹음 중 페이지 이탈 방지 |
| Waveform | `recording/Waveform.svelte` | 실시간 파형 시각화 (Canvas, 15fps) |
| AgendaTracker | `recording/AgendaTracker.svelte` | 안건 진행 추적 UI |

#### 5.2.3 필기 관련

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| TldrawWrapper | `sketch/TldrawWrapper.svelte` | tldraw React 브릿지 (ShadowDOM) |
| SketchPad | `sketch/SketchPad.svelte` | 필기 패드 컨테이너 |
| SketchToolbar | `sketch/SketchToolbar.svelte` | 필기 도구 툴바 |

#### 5.2.4 회의록 관련

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| TranscriptViewer | `results/TranscriptViewer.svelte` | 전사록 뷰어 (화자별 색상) |
| SummaryEditor | `results/SummaryEditor.svelte` | 회의록 편집기 |
| ActionItems | `results/ActionItems.svelte` | 액션아이템 목록/관리 |
| SpeakerMapper | `results/SpeakerMapper.svelte` | 화자 레이블 → 연락처 매핑 UI |

#### 5.2.5 오프라인/동기화

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| OfflineSyncManager | `OfflineSyncManager.svelte` | 오프라인 동기화 관리자 |
| SyncConflictDialog | `SyncConflictDialog.svelte` | 동기화 충돌 해결 다이얼로그 |

#### 5.2.6 기타

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| DarkModeToggle | `DarkModeToggle.svelte` | 다크모드 토글 |
| QuickJump | `QuickJump.svelte` | 키보드 단축키 검색 (Cmd+K) |
| PreflightCheck | `PreflightCheck.svelte` | 녹음 전 환경 체크 (마이크, 저장공간) |

### 5.3 Svelte Stores (8개)

| Store | 파일 | 설명 |
|-------|------|------|
| auth | `stores/auth.ts` | 인증 상태 (토큰, 사용자 정보) |
| meeting | `stores/meeting.ts` | 회의 목록, 현재 회의 상태 |
| recording | `stores/recording.ts` | 녹음 상태 (mediaRecorder, 파형 데이터) |
| results | `stores/results.ts` | 회의록, 전사록 데이터 |
| sketch | `stores/sketch.ts` | tldraw 상태 |
| contacts | `stores/contacts.ts` | 연락처 목록 |
| offline | `stores/offline.ts` | 오프라인 상태, 동기화 큐 |
| toast | `stores/toast.ts` | 토스트 메시지 큐 |

### 5.4 유틸리티

| 파일 | 설명 |
|------|------|
| `utils/api.ts` | API 클라이언트 (fetch wrapper, 토큰 자동 주입) |
| `utils/indexed-db.ts` | IndexedDB 래퍼 (녹음, 오프라인 캐시) |
| `utils/audio.ts` | 오디오 처리 유틸 (파형 추출, 청크 분할) |
| `utils/date.ts` | 날짜 포맷팅 |
| `utils/validation.ts` | 폼 검증 |

---

## 6. 비즈니스 로직

### 6.1 회의 라이프사이클

```
┌─────────────┐
│    DRAFT    │  ← 새 회의 생성
└──────┬──────┘
       │ 사용자: "녹음 시작" 클릭
       ▼
┌─────────────┐
│ IN_PROGRESS │  ← 녹음 진행 중
└──────┬──────┘
       │ 사용자: "녹음 중지" + 업로드 완료
       ▼
┌─────────────┐
│  COMPLETED  │  ← STT/LLM 처리 → 회의록 생성
└─────────────┘
```

**상태 전이 규칙:**

- `draft` → `in_progress`: 녹음 시작 시 자동 전이
- `in_progress` → `completed`: 녹음 업로드 완료 + 사용자 수동 전이
- 역방향 전이는 불가

### 6.2 녹음 업로드 프로토콜 (TUS-like)

```
1. [Frontend] POST /meetings/{id}/recordings
   → 서버: 녹음 메타데이터 생성, safe_filename 발급
   → Response: { upload_id, upload_url }

2. [Frontend] 녹음 데이터를 청크로 분할 (예: 5MB 단위)

3. [Frontend] POST /recordings/{id}/upload (청크 반복)
   Headers:
     - Upload-Offset: 현재 오프셋 (bytes)
     - Upload-Length: 전체 파일 크기 (첫 청크만)
   Body: 청크 데이터 (binary)

   → 서버: 파일에 청크 추가
   → Response: { bytes_received, total_bytes, is_complete }

4. [Frontend] is_complete=true가 되면 업로드 종료
   → 서버: checksum 검증, status='uploaded'로 변경

5. [Backend] Celery 작업 자동 트리거
   → stt_task.delay(recording_id)
```

**재개 지원 (Resume):**

```
[Frontend] HEAD /recordings/{id}/upload
→ Response Headers:
  - Upload-Offset: 123456 (현재 서버에 저장된 바이트 수)
  - Upload-Length: 500000

→ Frontend는 Upload-Offset부터 재개
```

### 6.3 STT 파이프라인

```
┌──────────────────────────────────────────────────────────────┐
│ Celery Task: stt_task(recording_id)                          │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. 녹음 파일 로드 (/data/max-meeting/recordings/...)        │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. 파일을 청크로 분할 (10분 단위)                            │
│    → audio_chunks = split_audio(file, chunk_minutes=10)      │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. faster-whisper STT (병렬 처리, max_parallel=4)            │
│    → segments = whisper.transcribe(chunk)                    │
│    → [{start, end, text}, ...]                              │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. pyannote.audio 화자분리 (Speaker Diarization)             │
│    → speaker_labels = diarization(chunk)                     │
│    → segments에 speaker 추가                                 │
│    → [{start, end, text, speaker: "SPEAKER_00"}, ...]       │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Transcript 레코드 저장 (JSONB)                            │
│    → INSERT INTO transcripts (segments, chunk_index)         │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. Redis Pub/Sub로 진행 상황 전송                            │
│    → redis.publish(f"stt_progress:{recording_id}", {         │
│        status: "processing",                                 │
│        progress: 50,                                          │
│        message: "청크 2/4 처리 중..."                         │
│      })                                                       │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. 모든 청크 완료 → recording.status = 'completed'           │
│    → 다음 단계: LLM 회의록 생성 트리거                        │
└──────────────────────────────────────────────────────────────┘
```

**SSE (Server-Sent Events) 구독:**

```javascript
const eventSource = new EventSource(`/api/v1/recordings/${id}/progress`);

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  console.log(data.message, data.progress);
});

eventSource.addEventListener('error', (event) => {
  eventSource.close();
});
```

### 6.4 LLM 회의록 생성 흐름

```
┌──────────────────────────────────────────────────────────────┐
│ Celery Task: generate_meeting_result(meeting_id)             │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. 전사록 전체 텍스트 추출                                    │
│    → SELECT segments FROM transcripts WHERE meeting_id=...   │
│    → full_text = concat_all_segments()                       │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. 안건 정보 로드                                             │
│    → SELECT * FROM agendas WHERE meeting_id=...              │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Gemini Flash 프롬프트 생성                                 │
│    → prompt = f"""                                            │
│       회의 제목: {meeting.title}                              │
│       안건:                                                   │
│       {agendas}                                               │
│                                                               │
│       전사록:                                                 │
│       {full_text}                                             │
│                                                               │
│       다음을 JSON으로 출력:                                   │
│       {                                                       │
│         "summary": "전체 요약",                               │
│         "decisions": [{"content": "...", "type": "..."}],    │
│         "action_items": [{"content": "...", "assignee": ...}]│
│       }                                                       │
│       """                                                     │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Gemini API 호출                                            │
│    → response = gemini.generate_content(prompt)              │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. JSON 파싱 및 DB 저장                                       │
│    → INSERT INTO meeting_results (summary, version=1)        │
│    → INSERT INTO meeting_decisions (content, type)           │
│    → INSERT INTO action_items (content, assignee_id, ...)   │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. 사용자 알림 (WebSocket or 폴링)                            │
│    → "회의록이 생성되었습니다. 검토해주세요."                 │
└──────────────────────────────────────────────────────────────┘
```

#### 6.4.1 회의록 생성 - 확장 출력 형식

**프롬프트 출력 형식 (meeting_insights 추가):**

```json
{
  "summary": "전체 회의 요약",
  "discussions": [{"agenda_idx": 0, "content": "..."}],
  "decisions": [{"agenda_idx": 0, "content": "...", "type": "approved|postponed|rejected"}],
  "action_items": [{"agenda_idx": 0, "assignee": "...", "content": "...", "due_date": "YYYY-MM-DD", "priority": "high|medium|low"}],
  "meeting_insights": {
    "atmosphere": "positive|neutral|tense",
    "consensus_level": 85,
    "key_turning_points": ["결정적 순간 1", "결정적 순간 2"],
    "top_contributors": ["발언자1", "발언자2", "발언자3"],
    "unresolved_concerns": ["미해결 이슈"]
  }
}
```

### 6.6 발언자 분석 파이프라인

```
┌──────────────────────────────────────────────────────────────┐
│ SpeakerAnalyticsService.analyze_speakers(segments)           │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. 발언자별 세그먼트 그룹화                                    │
│    → speakers = unique(segment.speaker for all segments)     │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. 기본 지표 계산                                             │
│    → total_speaking_time = sum(end - start)                  │
│    → turn_count = len(speaker_segments)                      │
│    → avg_turn_length = total_time / turn_count               │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. 질문 감지 (한국어 + 영어)                                   │
│    → 한국어: 습니까, 나요, 까요, 어때요 등                    │
│    → 영어: what, when, where, who + ?                        │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. 감정 분석                                                  │
│    → LLM 사용 가능: Gemini로 -1.0 ~ 1.0 점수 반환            │
│    → 폴백: 규칙 기반 (긍정/부정 키워드 카운트)                │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. 참여도 점수 계산 (0-100)                                   │
│    → participation_score = (turn_ratio * 60)                 │
│    → question_bonus = (question_ratio * 20)                  │
│    → turn_bonus = min(20, turns * 2)                         │
│    → total = min(100, participation + question + turn)       │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. 키워드 추출                                                │
│    → 불용어 제거 (한국어/영어)                                │
│    → 빈도 기반 상위 10개 추출                                 │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. SpeakerStats 객체 반환                                     │
│    → {speaker_id, total_speaking_time, turn_count,           │
│       questions_asked, sentiment_score, engagement_score,    │
│       dominant_topics, avg_turn_length}                      │
└──────────────────────────────────────────────────────────────┘
```

### 6.7 오프라인 동기화 프로토콜

**IndexedDB 스키마:**

```javascript
// Database: 'maxmeeting-offline'
{
  stores: [
    'meetings',      // 오프라인 캐시
    'recordings',    // 녹음 데이터 (임시 저장)
    'sync_queue',    // 동기화 대기 큐
    'conflicts'      // 충돌 해결 대기
  ]
}
```

**동기화 흐름:**

```
1. [오프라인 상태]
   → 사용자 액션 (회의 생성, 녹음 등)
   → IndexedDB에 저장 + sync_queue에 추가
   → { id, type: 'create_meeting', payload: {...}, timestamp }

2. [온라인 복귀]
   → OfflineSyncManager 감지 (navigator.onLine)
   → sync_queue 순회

3. [순차 동기화]
   for (const item of sync_queue) {
     try {
       await syncItem(item);
       // 성공 시 sync_queue에서 제거
     } catch (conflict) {
       // 충돌 감지 (서버 버전 > 클라이언트 버전)
       → conflicts에 추가
       → SyncConflictDialog 표시
       → 사용자 선택: "서버 우선" / "내 변경 우선" / "병합"
     }
   }
```

**충돌 해결:**

```javascript
// 서버 버전: updated_at=2026-01-30T10:00:00
// 클라이언트 버전: updated_at=2026-01-30T09:50:00 (오프라인 중 수정)

// 옵션 1: 서버 우선
→ 클라이언트 변경 폐기, 서버 데이터 덮어쓰기

// 옵션 2: 내 변경 우선
→ PATCH /api/v1/meetings/{id} (If-Unmodified-Since 헤더)
→ 서버가 409 Conflict 반환하면 → 옵션 1로 fallback

// 옵션 3: 병합
→ 사용자가 수동으로 필드별 선택
→ PATCH /api/v1/meetings/{id} (병합된 데이터)
```

---

## 7. 인증 및 보안

### 7.1 JWT 인증 흐름

```
┌─────────────┐                           ┌─────────────┐
│   Client    │                           │   Server    │
└──────┬──────┘                           └──────┬──────┘
       │                                         │
       │  POST /auth/login                       │
       │  { password: "..." }                    │
       ├────────────────────────────────────────>│
       │                                         │
       │                                  (bcrypt.verify)
       │                                  (JWT 토큰 생성)
       │                                         │
       │  { access_token, refresh_token }        │
       │<────────────────────────────────────────┤
       │                                         │
  (localStorage에 저장)                           │
       │                                         │
       │  GET /api/v1/meetings                   │
       │  Authorization: Bearer {access_token}   │
       ├────────────────────────────────────────>│
       │                                         │
       │                                  (JWT 검증)
       │                                  (user_id 추출)
       │                                         │
       │  { data: [...] }                        │
       │<────────────────────────────────────────┤
       │                                         │
  (access_token 만료)                             │
       │                                         │
       │  POST /auth/refresh                     │
       │  Authorization: Bearer {refresh_token}  │
       ├────────────────────────────────────────>│
       │                                         │
       │                                  (refresh_token 검증)
       │                                  (새 토큰 발급)
       │                                         │
       │  { access_token, refresh_token }        │
       │<────────────────────────────────────────┤
       │                                         │
```

**JWT Payload:**

```json
{
  "sub": "1",              // user_id
  "type": "access",        // "access" or "refresh"
  "exp": 1738233600,       // expiry timestamp
  "iat": 1738230000,       // issued at
  "iss": "max-meeting-api",
  "aud": "max-meeting"
}
```

**토큰 만료 시간:**

- Access Token: 60분 (기본값, 환경변수로 조정 가능)
- Refresh Token: 7일

### 7.2 PII 암호화 (pgcrypto)

**암호화 대상:**

- `contacts.phone_encrypted`
- `contacts.email_encrypted`

**암호화 방식:**

```sql
-- 암호화 (INSERT/UPDATE 시)
INSERT INTO contacts (name, phone_encrypted, email_encrypted)
VALUES (
  '홍길동',
  pgp_sym_encrypt('010-1234-5678', :encryption_key),
  pgp_sym_encrypt('hong@example.com', :encryption_key)
);

-- 복호화 (SELECT 시)
SELECT
  id,
  name,
  pgp_sym_decrypt(phone_encrypted, :encryption_key) AS phone,
  pgp_sym_decrypt(email_encrypted, :encryption_key) AS email
FROM contacts;
```

**키 관리:**

- 환경변수 `PII_ENCRYPTION_KEY` (최소 32바이트)
- Docker secrets로 주입 (`/run/secrets/pii_encryption_key`)
- 키 유출 시 전체 PII 데이터 재암호화 필요

### 7.3 Rate Limiting

**Redis 기반 Token Bucket 알고리즘**

| 엔드포인트 | 제한 | 범위 |
|----------|------|------|
| `POST /auth/login` | 5 req/min | IP 주소 |
| `POST /auth/refresh` | 10 req/min | IP 주소 |
| `POST /recordings/{id}/upload` | 10 req/hour | IP 주소 |
| `POST /agendas/*/parse*` (LLM) | 30 req/hour | 사용자 |
| 기타 모든 엔드포인트 | 200 req/min | 사용자 |

**구현:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)

@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...
```

**초과 시 응답:**

```json
HTTP 429 Too Many Requests
{
  "detail": "Rate limit exceeded. Try again in 45 seconds."
}
```

### 7.4 CORS 정책

**허용 Origin:**

```python
CORS_ORIGINS = [
  "http://localhost:5173",  # 개발 (Vite)
  "http://localhost:3000",  # 프로덕션 (Node adapter)
  "https://meeting.etlab.kr"  # 실제 도메인
]
```

**허용 메소드:** `GET, POST, PATCH, DELETE, OPTIONS`

**허용 헤더:** `Authorization, Content-Type, X-Request-ID`

**Credentials:** `true` (쿠키, Authorization 헤더 허용)

### 7.5 보안 헤더

```python
# Content Security Policy
CSP = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"

# X-Frame-Options
X_FRAME_OPTIONS = "DENY"

# X-Content-Type-Options
X_CONTENT_TYPE_OPTIONS = "nosniff"

# Referrer-Policy
REFERRER_POLICY = "strict-origin-when-cross-origin"
```

---

## 8. 설정 및 환경변수

### 8.1 백엔드 환경변수

**파일 위치:** `backend/.env`

#### 기본 설정

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `APP_ENV` | 환경 (development/production/test) | `development` | O |
| `DEBUG` | 디버그 모드 | `false` | - |
| `SECRET_KEY` | 애플리케이션 시크릿 키 (32+ bytes) | - | O |
| `API_VERSION` | API 버전 | `v1` | - |

#### 인증

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `AUTH_PASSWORD_HASH` | bcrypt 해시된 비밀번호 | - | O |
| `JWT_SECRET` | JWT 서명 키 (32+ bytes) | - | O |
| `JWT_ALGORITHM` | JWT 알고리즘 | `HS256` | - |
| `JWT_ACCESS_EXPIRE_MINUTES` | Access token 만료 시간 (분) | `60` | - |
| `JWT_REFRESH_EXPIRE_DAYS` | Refresh token 만료 시간 (일) | `7` | - |

#### 데이터베이스

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `DATABASE_URL` | PostgreSQL 연결 URL | - | O |
| `DB_POOL_SIZE` | 커넥션 풀 크기 | `5` | - |
| `DB_MAX_OVERFLOW` | 최대 추가 커넥션 | `10` | - |

**예시:**
```
DATABASE_URL=postgresql://maxmeeting:password@localhost:5432/maxmeeting
```

#### Redis / Celery

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379/0` | O |
| `REDIS_PASSWORD` | Redis 비밀번호 | - | - |
| `CELERY_BROKER_URL` | Celery 브로커 URL | `redis://localhost:6379/0` | O |
| `CELERY_TASK_TIME_LIMIT` | 작업 최대 실행 시간 (초) | `7200` | - |
| `CELERY_WORKER_CONCURRENCY` | 워커 동시 실행 수 | `1` | - |

#### 파일 저장

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `STORAGE_BACKEND` | 저장소 (local/s3) | `local` | - |
| `STORAGE_PATH` | 로컬 저장 경로 | `/data/max-meeting` | O |
| `RECORDINGS_PATH` | 녹음 파일 경로 | `/data/max-meeting/recordings` | O |
| `MAX_UPLOAD_SIZE_MB` | 최대 업로드 크기 (MB) | `500` | - |

#### STT

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `WHISPER_MODEL` | Whisper 모델 크기 | `medium` | - |
| `WHISPER_DEVICE` | 실행 디바이스 (cpu/cuda) | `cpu` | - |
| `STT_CHUNK_MINUTES` | 청크 분할 단위 (분) | `10` | - |
| `STT_MAX_PARALLEL` | 최대 병렬 처리 수 | `4` | - |
| `HUGGINGFACE_TOKEN` | HuggingFace 토큰 (pyannote용) | - | O |

#### LLM

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `LLM_PROVIDER` | LLM 제공자 (gemini/openai) | `gemini` | - |
| `GEMINI_API_KEY` | Gemini API 키 | - | O (Gemini 사용 시) |
| `OPENAI_API_KEY` | OpenAI API 키 | - | O (OpenAI 사용 시) |

#### Rate Limiting

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `RATE_LIMIT_LOGIN` | 로그인 제한 | `5/minute` |
| `RATE_LIMIT_REFRESH` | 토큰 갱신 제한 | `10/minute` |
| `RATE_LIMIT_UPLOAD` | 업로드 제한 | `10/hour` |
| `RATE_LIMIT_LLM` | LLM API 제한 | `30/hour` |
| `RATE_LIMIT_DEFAULT` | 기본 제한 | `200/minute` |

#### CORS

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `CORS_ORIGINS` | 허용 Origin (JSON 배열) | `["http://localhost:5173","http://localhost:3000"]` |

#### 모니터링

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `SENTRY_DSN` | Sentry DSN | - |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |
| `LOG_FORMAT` | 로그 포맷 (json/text) | `json` |

#### PII 암호화

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `PII_ENCRYPTION_KEY` | PII 암호화 키 (32+ bytes) | - | O |

### 8.2 프론트엔드 환경변수

**파일 위치:** `frontend/.env`

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `PUBLIC_API_URL` | 백엔드 API URL | `http://localhost:8000/api/v1` | O |
| `PORT` | 서버 포트 | `3000` | - |
| `HOST` | 서버 호스트 | `0.0.0.0` | - |
| `ORIGIN` | CORS origin | `http://localhost:3000` | - |

**프로덕션 예시:**

```
PUBLIC_API_URL=https://api.meeting.etlab.kr/api/v1
PORT=3000
ORIGIN=https://meeting.etlab.kr
```

### 8.3 Docker Secrets

**파일 위치:** `docker/secrets/`

| 파일 | 설명 |
|------|------|
| `db_password.txt` | PostgreSQL 비밀번호 |
| `redis_password.txt` | Redis 비밀번호 |
| `jwt_secret.txt` | JWT 서명 키 |
| `gemini_api_key.txt` | Gemini API 키 |
| `huggingface_token.txt` | HuggingFace 토큰 |
| `pii_encryption_key.txt` | PII 암호화 키 |

**생성 방법:**

```bash
mkdir -p docker/secrets
echo "your-db-password" > docker/secrets/db_password.txt
echo "your-redis-password" > docker/secrets/redis_password.txt
echo "$(openssl rand -base64 32)" > docker/secrets/jwt_secret.txt
echo "your-gemini-api-key" > docker/secrets/gemini_api_key.txt
echo "your-hf-token" > docker/secrets/huggingface_token.txt
echo "$(openssl rand -base64 32)" > docker/secrets/pii_encryption_key.txt
chmod 600 docker/secrets/*.txt
```

---

## 9. 배포 가이드

### 9.1 Docker Compose 배포

**전제 조건:**

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM (STT 워커 포함)

**1단계: 환경 설정**

```bash
cd max-meeting

# Docker secrets 생성 (위 8.3 참조)
mkdir -p docker/secrets
# ... (secrets 생성)

# .env 파일 생성
cp .env.example docker/.env
vi docker/.env
```

**docker/.env 예시:**

```bash
# Application
SECRET_KEY=change-me-minimum-32-bytes-long
AUTH_PASSWORD_HASH=$2b$12$yourbcrypthashhere

# Database
DB_PASSWORD=your-db-password

# Redis
REDIS_PASSWORD=your-redis-password

# JWT
JWT_SECRET=your-jwt-secret-32-bytes

# Storage
STORAGE_PATH=/data/max-meeting

# CORS
CORS_ORIGINS=["https://meeting.etlab.kr","http://localhost:5173"]
```

**2단계: 서비스 시작**

```bash
cd docker
docker-compose up -d

# 또는 헬퍼 스크립트 사용
cd ..
./scripts/prod.sh start
```

**3단계: 초기화**

```bash
# 데이터베이스 마이그레이션
docker exec -it maxmeeting-app alembic upgrade head

# 기본 회의 유형 생성
docker exec -it maxmeeting-app python -m scripts.init_meeting_types
```

**4단계: 상태 확인**

```bash
# 모든 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f app

# 헬스체크
curl http://localhost:8000/api/v1/health
```

**5단계: 리버스 프록시 설정 (Caddy)**

```caddyfile
# /etc/caddy/Caddyfile
meeting.etlab.kr {
    reverse_proxy localhost:3000  # Frontend
}

api.meeting.etlab.kr {
    reverse_proxy localhost:8000  # Backend
}
```

```bash
sudo systemctl reload caddy
```

### 9.2 수동 빌드 및 실행

#### 백엔드

```bash
cd backend

# Python 가상환경 생성
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
vi .env

# 데이터베이스 마이그레이션
alembic upgrade head

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Celery 워커

```bash
cd backend
source venv/bin/activate

# STT/LLM 워커 실행
celery -A workers.celery_app worker \
  --loglevel=info \
  --concurrency=1 \
  --max-tasks-per-child=10
```

#### 프론트엔드

```bash
cd frontend

# 의존성 설치
npm install

# 환경변수 설정
cp .env.example .env
vi .env

# 빌드
npm run build

# 실행
PORT=3000 node build
```

### 9.3 Vercel 배포 (프론트엔드)

**vercel.json:**

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "build",
  "framework": "sveltekit",
  "env": {
    "PUBLIC_API_URL": "https://api.meeting.etlab.kr/api/v1"
  }
}
```

**배포:**

```bash
cd frontend
npm install -g vercel
vercel --prod
```

### 9.4 서비스 관리 (systemd)

**백엔드 서비스:**

```ini
# /etc/systemd/system/maxmeeting-api.service
[Unit]
Description=MAX Meeting FastAPI Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=maxmeeting
WorkingDirectory=/opt/maxmeeting/backend
Environment="PATH=/opt/maxmeeting/backend/venv/bin"
ExecStart=/opt/maxmeeting/backend/venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

**Celery 워커 서비스:**

```ini
# /etc/systemd/system/maxmeeting-worker.service
[Unit]
Description=MAX Meeting Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=maxmeeting
WorkingDirectory=/opt/maxmeeting/backend
Environment="PATH=/opt/maxmeeting/backend/venv/bin"
ExecStart=/opt/maxmeeting/backend/venv/bin/celery -A workers.celery_app worker \
  --loglevel=info \
  --concurrency=1 \
  --max-tasks-per-child=10
Restart=always

[Install]
WantedBy=multi-user.target
```

**활성화:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable maxmeeting-api.service
sudo systemctl enable maxmeeting-worker.service
sudo systemctl start maxmeeting-api.service
sudo systemctl start maxmeeting-worker.service
```

### 9.5 백업 및 복구

#### 데이터베이스 백업

```bash
# 백업
pg_dump -h localhost -U maxmeeting maxmeeting \
  | gzip > maxmeeting_$(date +%Y%m%d_%H%M%S).sql.gz

# 복구
gunzip < maxmeeting_20260130_100000.sql.gz \
  | psql -h localhost -U maxmeeting maxmeeting
```

#### 녹음 파일 백업 (rsync)

```bash
# 원격 서버로 동기화
rsync -avz --progress \
  /data/max-meeting/recordings/ \
  sean@192.168.35.249:/backup/max-meeting/recordings/

# cron 등록 (매시간)
0 * * * * /opt/maxmeeting/scripts/backup.sh
```

### 9.6 모니터링 및 로깅

#### Sentry 통합

```python
# backend/app/main.py (이미 구현됨)
import sentry_sdk

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=0.1,
    )
```

#### 로그 수집

```bash
# Docker logs → file
docker-compose logs -f app > /var/log/maxmeeting/app.log

# journald → file (systemd)
journalctl -u maxmeeting-api.service -f > /var/log/maxmeeting/api.log
```

---

## 부록

### A. 디렉토리 구조

```
max-meeting/
├── backend/                  # FastAPI 백엔드
│   ├── alembic/             # DB 마이그레이션
│   ├── app/
│   │   ├── auth/            # 인증 모듈
│   │   ├── middleware/      # 미들웨어 (rate limit 등)
│   │   ├── models/          # SQLAlchemy 모델 (15개 테이블)
│   │   ├── routers/         # API 라우터 (10개)
│   │   ├── schemas/         # Pydantic 스키마
│   │   ├── services/        # 비즈니스 로직
│   │   ├── config.py        # 설정
│   │   ├── database.py      # DB 연결
│   │   ├── errors.py        # 예외 핸들러
│   │   └── main.py          # FastAPI app
│   ├── workers/             # Celery 워커
│   │   ├── tasks/
│   │   │   ├── stt.py       # STT 작업
│   │   │   ├── llm.py       # LLM 작업
│   │   │   └── cleanup.py   # 정리 작업
│   │   └── celery_app.py    # Celery 설정
│   ├── tests/               # 테스트
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── requirements.txt     # Python 의존성
│   └── .env.example
│
├── frontend/                # SvelteKit 프론트엔드
│   ├── src/
│   │   ├── routes/          # 페이지 라우트 (13개)
│   │   ├── lib/
│   │   │   ├── components/  # Svelte 컴포넌트 (26개)
│   │   │   ├── stores/      # Svelte stores (8개)
│   │   │   └── utils/       # 유틸리티
│   │   ├── app.html         # HTML 템플릿
│   │   └── app.css          # 전역 스타일
│   ├── static/              # 정적 파일
│   ├── package.json
│   ├── svelte.config.js
│   ├── tailwind.config.js
│   └── .env.example
│
├── docker/                  # Docker 설정
│   ├── docker-compose.yml
│   ├── Dockerfile.app       # 백엔드 Dockerfile
│   ├── Dockerfile.worker    # Celery 워커 Dockerfile
│   ├── init.sql             # PostgreSQL 초기화 스크립트
│   └── secrets/             # Docker secrets
│       ├── db_password.txt
│       ├── jwt_secret.txt
│       └── ...
│
├── scripts/                 # 유틸리티 스크립트
│   ├── dev.sh               # 개발 서버 실행
│   ├── prod.sh              # 프로덕션 관리
│   └── backup.sh            # 백업 스크립트
│
├── .env.example             # 환경변수 템플릿
├── README.md
└── SPECIFICATION.md         # 본 문서
```

### B. 테스트 실행

#### 백엔드 테스트

```bash
cd backend
source venv/bin/activate

# 단위 테스트
pytest tests/unit/ -v

# 통합 테스트
pytest tests/integration/ -v

# 커버리지
pytest --cov=app --cov-report=html
```

#### 프론트엔드 테스트

```bash
cd frontend

# 단위 테스트
npm test

# 커버리지
npm run test:coverage
```

### C. 문제 해결

#### Q1. STT가 실패합니다.

**원인:**

- HUGGINGFACE_TOKEN이 없거나 만료됨
- 메모리 부족 (pyannote는 8GB+ 권장)

**해결:**

```bash
# 토큰 확인
echo $HUGGINGFACE_TOKEN

# 메모리 확인
free -h

# Docker 워커 메모리 증가
# docker-compose.yml → worker → deploy.resources.limits.memory: 12G
```

#### Q2. 녹음 업로드가 중단됩니다.

**원인:**

- 네트워크 불안정
- 청크 크기가 너무 큼

**해결:**

```javascript
// frontend/src/lib/stores/recording.ts
const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB → 1MB로 감소
```

#### Q3. 오프라인 동기화 충돌이 자주 발생합니다.

**원인:**

- 여러 기기에서 동시 수정
- updated_at 타임스탬프 불일치

**해결:**

```javascript
// 수동 동기화 트리거 지연
const SYNC_DEBOUNCE_MS = 5000; // 5초 대기 후 동기화
```

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0.0 | 2026-01-29 | 초안 작성 |
| 1.0.1 | 2026-01-29 | 안건 파싱 계층 구조 지원 추가, Python 버전 수정 (3.11), 테이블 개수 수정 (16개) |
| 1.0.2 | 2026-01-29 | 회의 인사이트 기능 추가 (분위기/합의/전환점), 발언자 분석 서비스 추가 (SpeakerAnalyticsService), 질문 생성 프롬프트 개선 (Few-shot 예시) |

---

**문서 작성자:** ET (@etlab.kr)
**최종 업데이트:** 2026-01-29
**문서 위치:** `/home/et/max-ops/max-meeting/SPECIFICATION.md`
