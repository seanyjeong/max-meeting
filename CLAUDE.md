# MAX Meeting - AI 회의 관리 시스템

## 프로젝트 개요

AI 기반 회의 관리 플랫폼. 음성 녹음 → STT 변환 → LLM 분석 → 회의록/인사이트 자동 생성.

## 기술 스택

### Backend
- **Framework**: FastAPI 0.109
- **DB**: PostgreSQL 16 + SQLAlchemy 2.0.25
- **Cache/Queue**: Redis 7 + Celery 5.3.6
- **STT**: faster-whisper (GPU 지원)
- **LLM**: Google Gemini (gemini-2.0-flash)
- **Auth**: JWT (access + refresh token)

### Frontend
- **Framework**: SvelteKit 2.0 + Svelte 5.0
- **Build**: Vite 5.4 + adapter-node
- **Sketch**: tldraw 4.3.8 (React bridge)
- **DnD**: svelte-dnd-action 0.9.54
- **Sanitize**: DOMPurify 3.2.4

### Infrastructure
- **Container**: Docker Compose
- **Reverse Proxy**: Caddy (ET서버)
- **Frontend Deploy**: Vercel (예정)

---

## 디렉토리 구조

```
max-meeting/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # 47개 API 엔드포인트
│   │   │   ├── auth.py      # 인증 (login, register, refresh, logout)
│   │   │   ├── users.py     # 사용자 CRUD
│   │   │   ├── meetings.py  # 회의 CRUD + 상태 관리
│   │   │   ├── agendas.py   # 안건 관리
│   │   │   ├── recordings.py # 녹음 업로드 (청크)
│   │   │   ├── transcripts.py # STT 결과
│   │   │   ├── results.py   # 회의록/요약
│   │   │   ├── sketches.py  # tldraw 스케치
│   │   │   ├── contacts.py  # 연락처 (PII 암호화)
│   │   │   ├── search.py    # 전문 검색 (pg_trgm)
│   │   │   └── ai.py        # LLM 질문/파싱 API
│   │   ├── models/          # 16개 SQLAlchemy 모델
│   │   ├── services/
│   │   │   ├── llm.py       # Gemini 연동 + 프롬프트
│   │   │   ├── stt.py       # faster-whisper 래퍼
│   │   │   └── speaker_analytics.py # 발언자 분석
│   │   ├── core/
│   │   │   ├── config.py    # 설정 (60+ 환경변수)
│   │   │   ├── security.py  # JWT, 암호화
│   │   │   └── deps.py      # 의존성 주입
│   │   └── workers/         # Celery 태스크
│   ├── tests/               # pytest (197 passed)
│   ├── alembic/             # DB 마이그레이션
│   └── .env                 # 환경변수 (gitignore)
│
├── frontend/
│   ├── src/
│   │   ├── routes/          # 13개 SvelteKit 페이지
│   │   │   ├── +page.svelte           # 대시보드
│   │   │   ├── auth/login/            # 로그인
│   │   │   ├── auth/register/         # 회원가입
│   │   │   ├── meetings/new/          # 회의 생성 + 안건 파싱
│   │   │   ├── meetings/[id]/         # 회의 상세
│   │   │   ├── meetings/[id]/record/  # 녹음 페이지
│   │   │   ├── meetings/[id]/results/ # 결과 페이지
│   │   │   ├── meetings/[id]/sketch/  # 스케치 페이지
│   │   │   └── search/                # 검색 페이지
│   │   ├── lib/
│   │   │   ├── api.ts       # API 클라이언트 (401 인터셉터)
│   │   │   ├── stores/      # 8개 Svelte 스토어
│   │   │   │   ├── auth.ts      # 인증 상태 + refreshToken()
│   │   │   │   ├── meetings.ts  # 회의 목록
│   │   │   │   ├── recording.ts # 녹음 상태 + uploadRecording()
│   │   │   │   └── toast.ts     # 전역 토스트
│   │   │   └── components/  # 26개 컴포넌트
│   │   │       ├── AgendaEditor.svelte  # DnD 안건 편집기
│   │   │       ├── Toast.svelte
│   │   │       ├── recording/   # 녹음 관련
│   │   │       └── results/     # 결과 관련
│   │   └── app.html
│   ├── static/
│   └── svelte.config.js     # adapter-node
│
├── docker/
│   ├── docker-compose.yml   # 전체 스택
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
│
├── scripts/
│   ├── dev.sh               # 개발 서버 실행
│   └── prod.sh              # Docker 관리
│
├── SPECIFICATION.md         # 전체 명세서 (600+ lines)
└── CLAUDE.md                # 이 파일
```

---

## 핵심 기능

### 1. 회의 생성 + 안건 파싱

**경로**: `frontend/src/routes/meetings/new/+page.svelte`

사용자가 텍스트를 붙여넣으면 LLM이 자동 파싱:

```
입력:
1. 예산안 심의
   - 2024년 예산 검토
   - 비용 절감 방안
2. 인사 발표

출력:
[
  {"title": "예산안 심의", "description": "- 2024년 예산 검토\n- 비용 절감 방안"},
  {"title": "인사 발표", "description": ""}
]
```

**지원 형식**:
- 숫자: 1. 2. 3.
- 로마자: I. II. III.
- 한글: 가. 나. 다. / 제1조, 제2조
- 원문자: ① ② ③
- 괄호: (1) (2) / a) b)
- 비구조화 텍스트 → 맥락 분석 후 자동 그룹화

**하이브리드 워크플로우**:
1. 텍스트 입력 → 500ms debounce → LLM 파싱
2. AgendaEditor에서 드래그앤드롭 조정
3. 병합/분할 버튼으로 미세 조정
4. Ctrl+Z로 undo (최대 20개)

### 2. 녹음 + STT

**경로**: `frontend/src/routes/meetings/[id]/record/+page.svelte`

- MediaRecorder API로 녹음
- 실시간 파형 시각화
- 청크 업로드 (5MB 단위)
- 진행률 표시
- 업로드 완료 → Celery 워커가 STT 처리

**백엔드**: `backend/app/services/stt.py`
- faster-whisper 사용
- GPU 가속 지원
- 화자 분리 (diarization)

### 3. LLM 분석

**경로**: `backend/app/services/llm.py`

| 기능 | 메서드 | 설명 |
|------|--------|------|
| 질문 생성 | `generate_questions()` | 안건별 맞춤 질문 5개 |
| 안건 파싱 | `parse_agenda_text()` | 복잡 형식 + 맥락 그룹화 |
| 회의록 생성 | `generate_summary()` | 요약 + 결정사항 |
| 인사이트 추출 | `extract_meeting_insights()` | 분위기, 합의도, 전환점 |

**프롬프트 특징**:
- 10년+ 경력 비서 역할
- Few-shot 예시 3개 (예산, 채용, 프로젝트)
- 한국어 최적화

### 4. 결과 페이지

**경로**: `frontend/src/routes/meetings/[id]/results/+page.svelte`

- 트랜스크립트 뷰어 (타임스탬프 클릭 → 해당 위치 재생)
- 요약 에디터 (마크다운)
- 화자 매핑 (SpeakerMapper 컴포넌트)
- 인사이트 카드 (분위기, 합의도, 핵심 기여자)

### 5. 스케치

**경로**: `frontend/src/routes/meetings/[id]/sketch/+page.svelte`

- tldraw 4.x 통합 (React → Svelte 브릿지)
- 자동 저장
- 회의별 독립 캔버스

---

## API 엔드포인트 (주요)

### Auth
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/auth/login` | 로그인 |
| POST | `/api/v1/auth/register` | 회원가입 |
| POST | `/api/v1/auth/refresh` | 토큰 갱신 |
| POST | `/api/v1/auth/logout` | 로그아웃 |

### Meetings
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/meetings` | 목록 조회 |
| POST | `/api/v1/meetings` | 생성 |
| GET | `/api/v1/meetings/{id}` | 상세 조회 |
| PATCH | `/api/v1/meetings/{id}` | 수정 |
| DELETE | `/api/v1/meetings/{id}` | 삭제 |
| POST | `/api/v1/meetings/{id}/start` | 시작 |
| POST | `/api/v1/meetings/{id}/end` | 종료 |

### Recordings
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/recordings/upload-chunk` | 청크 업로드 |
| POST | `/api/v1/recordings/complete` | 업로드 완료 |
| GET | `/api/v1/recordings/{id}/status` | 처리 상태 |

### AI
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/ai/generate-questions` | 질문 생성 |
| POST | `/api/v1/ai/parse-agenda` | 안건 파싱 |
| POST | `/api/v1/ai/summarize` | 요약 생성 |

---

## 데이터베이스 스키마 (주요 테이블)

### users
| Column | Type | 설명 |
|--------|------|------|
| id | UUID | PK |
| email | VARCHAR(255) | UNIQUE |
| hashed_password | VARCHAR(255) | bcrypt |
| name | VARCHAR(100) | |
| is_active | BOOLEAN | |

### meetings
| Column | Type | 설명 |
|--------|------|------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| title | VARCHAR(255) | |
| status | ENUM | draft/scheduled/in_progress/completed |
| scheduled_at | TIMESTAMP | |
| started_at | TIMESTAMP | |
| ended_at | TIMESTAMP | |

### agendas
| Column | Type | 설명 |
|--------|------|------|
| id | UUID | PK |
| meeting_id | UUID | FK → meetings |
| title | VARCHAR(255) | |
| description | TEXT | 하위 항목 포함 |
| duration_minutes | INTEGER | |
| order | INTEGER | |

### recordings
| Column | Type | 설명 |
|--------|------|------|
| id | UUID | PK |
| meeting_id | UUID | FK → meetings |
| file_path | VARCHAR(500) | |
| status | ENUM | uploading/processing/completed/failed |
| duration_seconds | INTEGER | |

### transcripts
| Column | Type | 설명 |
|--------|------|------|
| id | UUID | PK |
| recording_id | UUID | FK → recordings |
| content | TEXT | 전체 텍스트 |
| segments | JSONB | 타임스탬프별 세그먼트 |
| speakers | JSONB | 화자 정보 |

---

## 환경변수

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/maxmeeting
ASYNC_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/maxmeeting

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Gemini
GEMINI_API_KEY=AIzaSy...

# STT
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda  # or cpu

# Storage
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE=500MB

# Security
PII_ENCRYPTION_KEY=your-encryption-key
```

### Frontend (.env)
```bash
PUBLIC_API_URL=http://localhost:8000
PUBLIC_WS_URL=ws://localhost:8000
```

---

## 실행 방법

### 개발 환경
```bash
# 전체 실행
./scripts/dev.sh all

# 개별 실행
./scripts/dev.sh backend   # FastAPI + Celery
./scripts/dev.sh frontend  # SvelteKit dev server
```

### 프로덕션 (Docker)
```bash
# 시작
./scripts/prod.sh start

# 재시작
./scripts/prod.sh restart

# 로그
./scripts/prod.sh logs

# 중지
./scripts/prod.sh stop
```

### Docker 컨테이너
| 컨테이너 | 포트 | 역할 |
|----------|------|------|
| maxmeeting-app | 8000 | FastAPI |
| maxmeeting-worker | - | Celery |
| maxmeeting-db | 5432 | PostgreSQL |
| maxmeeting-redis | 6379 | Redis |
| maxmeeting-frontend | 3000 | SvelteKit |

---

## 테스트

### Backend
```bash
cd backend
pytest                    # 전체 (197 tests)
pytest tests/unit/       # 유닛 테스트만
pytest -k "test_auth"    # 특정 패턴
```

### Frontend
```bash
cd frontend
npm run check            # TypeScript 타입 체크
npm run build            # 프로덕션 빌드
npm run test             # Playwright E2E
```

---

## 보안 체크리스트

- [x] JWT 토큰 자동 갱신 (401 인터셉터)
- [x] XSS 방지 (DOMPurify)
- [x] Path Traversal 방지 (sketches.py)
- [x] MIME 타입 검증 (파일 업로드)
- [x] Rate Limiting
- [x] PII 암호화 (연락처)
- [x] 보안 헤더 (X-Content-Type-Options, X-Frame-Options)
- [ ] CSP 헤더 (권장)
- [ ] httpOnly 쿠키 전환 (권장)

---

## 알려진 이슈

1. **a11y 경고 4개** - click 이벤트에 keyboard 핸들러 누락 (기능에 영향 없음)
2. **OpenAI 프로바이더 미구현** - Gemini만 지원
3. **오프라인 동기화 미완성** - IndexedDB는 있으나 sync 로직 부분적

---

## 배포 계획

### Backend (ET 서버)
- Docker Compose로 실행
- Caddy 리버스 프록시
- 도메인: `maxmeeting.etlab.kr` (예정)

### Frontend (Vercel)
- adapter-node → adapter-vercel 전환 필요
- 또는 현재 adapter-node로 ET 서버에서 직접 호스팅

---

## 관련 문서

| 문서 | 설명 |
|------|------|
| [SPECIFICATION.md](./SPECIFICATION.md) | 전체 기술 명세서 - API 47개, DB 16테이블, 컴포넌트 26개 상세 |
| [README.md](./README.md) | 설치 및 실행 가이드 |
| [backend/.env.example](./backend/.env.example) | 백엔드 환경변수 템플릿 |
| [frontend/.env.example](./frontend/.env.example) | 프론트엔드 환경변수 템플릿 |
| [docker/docker-compose.yml](./docker/docker-compose.yml) | Docker 스택 구성 |

---

## 연락처

- **프로젝트 위치**: `/home/et/max-ops/max-meeting`
- **명세서**: `SPECIFICATION.md`
- **이 문서**: `CLAUDE.md`
