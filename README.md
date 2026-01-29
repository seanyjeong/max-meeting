# MAX Meeting

회의 관리 SaaS - 안건 등록부터 자동 정리까지

## 개요

MAX Meeting은 회의 전체 워크플로우를 하나의 웹앱에서 처리하는 솔루션입니다.

- **회의 전**: 안건 등록 → LLM이 질문지 자동 생성
- **회의 중**: 녹음 + 펜슬 필기 + 타이핑 메모
- **회의 후**: STT → LLM 회의록 자동 생성 → 사용자 검증 → 저장

## 기술 스택

| 구분 | 기술 |
|------|------|
| 프론트엔드 | SvelteKit 5 + Svelte 5 (Runes), TailwindCSS |
| 필기 도구 | tldraw v4 (React 브릿지) |
| 백엔드 | FastAPI + SQLAlchemy (비동기) |
| DB | PostgreSQL 16 (pg_trgm + pgcrypto) |
| 캐시/큐 | Redis 7 + Celery |
| STT | faster-whisper (medium) + pyannote |
| LLM | Gemini Flash |
| 컨테이너 | Docker + Docker Compose |

## 프로젝트 구조

```
max-meeting/
├── backend/           # FastAPI 백엔드
│   ├── app/
│   │   ├── routers/   # API 엔드포인트 (10개)
│   │   ├── services/  # 비즈니스 로직
│   │   ├── models/    # DB 모델 (15개 테이블)
│   │   └── schemas/   # Pydantic 스키마
│   ├── workers/       # Celery 워커 (STT, LLM)
│   ├── alembic/       # DB 마이그레이션
│   └── tests/         # pytest 테스트
├── frontend/          # SvelteKit 프론트엔드
│   ├── src/
│   │   ├── routes/    # 페이지 라우트 (12개)
│   │   └── lib/
│   │       ├── components/  # 재사용 컴포넌트 (24개)
│   │       ├── stores/      # Svelte stores (8개)
│   │       └── utils/       # 유틸리티
│   └── build/         # 프로덕션 빌드 출력
├── docker/            # Docker 설정
│   ├── docker-compose.yml
│   ├── Dockerfile.app
│   ├── Dockerfile.worker
│   └── secrets/       # Docker secrets
├── scripts/           # 유틸리티 스크립트
│   ├── dev.sh         # 개발 서버 시작
│   └── prod.sh        # 프로덕션 관리
└── .env.example       # 환경 변수 템플릿
```

## 빠른 시작

### 1. 환경 설정

```bash
# 레포지토리 클론
git clone <repository-url>
cd max-meeting

# .env 파일 생성
cp .env.example .env
# .env 파일 편집하여 실제 값 입력
```

### 2. 개발 서버 실행

```bash
# 전체 실행 (백엔드 + 프론트엔드)
./scripts/dev.sh all

# 또는 개별 실행
./scripts/dev.sh backend   # http://localhost:8000
./scripts/dev.sh frontend  # http://localhost:5173
```

### 3. 수동 실행 (개발)

**백엔드:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**프론트엔드:**
```bash
cd frontend
npm install
npm run dev
```

## 프로덕션 배포

### Docker Compose 배포

```bash
# Docker secrets 생성
mkdir -p docker/secrets
echo "your-db-password" > docker/secrets/db_password.txt
echo "your-redis-password" > docker/secrets/redis_password.txt
echo "your-jwt-secret-min-32-bytes" > docker/secrets/jwt_secret.txt
echo "your-gemini-api-key" > docker/secrets/gemini_api_key.txt
echo "your-huggingface-token" > docker/secrets/huggingface_token.txt
chmod 600 docker/secrets/*.txt

# .env 파일 생성
cp .env.example docker/.env
# docker/.env 편집

# 서비스 시작
./scripts/prod.sh start

# 상태 확인
./scripts/prod.sh status

# 로그 확인
./scripts/prod.sh logs

# 서비스 중지
./scripts/prod.sh stop
```

### 수동 빌드

**프론트엔드 빌드:**
```bash
cd frontend
npm run build
# 빌드 결과: build/ 디렉토리
node build  # 실행
```

**백엔드 실행:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 환경 변수

주요 환경 변수 (`.env.example` 참조):

| 변수 | 설명 |
|------|------|
| `SECRET_KEY` | 앱 시크릿 키 (32+ bytes) |
| `AUTH_PASSWORD_HASH` | 비밀번호 bcrypt 해시 |
| `JWT_SECRET` | JWT 시크릿 (32+ bytes) |
| `DATABASE_URL` | PostgreSQL 연결 URL |
| `REDIS_URL` | Redis 연결 URL |
| `GEMINI_API_KEY` | Google Gemini API 키 |
| `HUGGINGFACE_TOKEN` | pyannote 화자분리용 토큰 |

## API 문서

서버 실행 후 자동 생성되는 API 문서:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 주요 기능

### 회의 관리
- 회의 유형 관리 (주간회의, 프로젝트 회의 등)
- 참석자 관리 (연락처 연동)
- 소프트 삭제 및 복원

### 안건 관리
- 안건 CRUD + 순서 변경
- LLM 질문 자동 생성
- 안건별 타임스탬프 추적

### 녹음
- 브라우저 MediaRecorder API
- 실시간 파형 시각화 (15fps)
- IndexedDB 자동 저장 (5분마다)
- 배터리 경고 + Wake Lock

### 필기 (tldraw)
- React-Svelte 브릿지
- 펜슬 자동 감지
- JSONB 저장/로드

### STT + 회의록
- faster-whisper (medium, CPU int8)
- pyannote 화자분리
- Gemini Flash 요약 생성
- 수동 편집 + 버전 관리

## 테스트

```bash
# 백엔드 테스트
cd backend
source venv/bin/activate
pytest tests/unit/ -v

# 프론트엔드 테스트
cd frontend
npm test
```

## 구현 상태

- **백엔드**: 95% 완성 (40+ API 엔드포인트)
- **프론트엔드**: 85% 완성 (12 페이지, 24 컴포넌트)
- **테스트**: 약 70% 커버리지

### 완료된 기능
- [x] JWT 인증 + Rate Limiting
- [x] 회의 CRUD + 소프트 삭제
- [x] 안건 관리 + 질문 생성
- [x] 연락처 관리 (PII 암호화)
- [x] 녹음 UI + 파형 표시
- [x] tldraw 필기
- [x] STT 파이프라인
- [x] 회의록 편집 UI
- [x] 전문 검색 (pg_trgm)
- [x] 오프라인 지원 (PWA)

## 문서

- 기획서: `.omc/plans/meeting-saas-production.md`
- 회의 유형 구현: `MEETING_TYPES_IMPLEMENTATION.md`
- DB 스키마: 기획서 섹션 7 참조

## 라이선스

개인 사용 목적.

> **주의**: pyannote-audio는 개인/연구 목적은 무료이나, 상업적 사용 시 별도 라이선스가 필요합니다.

## 작성자

ET (@etlab.kr)
