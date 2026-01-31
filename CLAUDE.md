# MAX Meeting - AI 회의 관리 시스템

> 음성 녹음 → STT → LLM 분석 → 회의록 자동 생성

## Quick Reference

| 구분 | 값 |
|------|-----|
| **Version** | v1.16.6 (2026-01-31) |
| **Backend** | FastAPI @ `localhost:9000` |
| **Frontend** | SvelteKit @ Vercel (`max-meeting.vercel.app`) |
| **DB** | PostgreSQL @ `localhost:5432/maxmeeting` |
| **API Base** | `https://api.meeting.etlab.kr/api/v1` |

## 상세 문서

| 문서 | 내용 |
|------|------|
| [docs/BACKEND.md](docs/BACKEND.md) | API 58개, 서비스 구조, 환경변수 |
| [docs/FRONTEND.md](docs/FRONTEND.md) | 라우트 13개, 컴포넌트 43개, 스토어 9개 |
| [docs/DATABASE.md](docs/DATABASE.md) | 테이블 17개, 스키마, 관계도 |
| [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) | 서버, 포트, systemd, Caddy, 배포 |

---

## 핵심 경로

```
backend/
├── app/api/v1/     # API 라우터 (10개 파일)
├── app/models/     # SQLAlchemy 모델 (11개)
├── app/services/   # 비즈니스 로직 (12개: llm, stt, recording 등)
├── workers/tasks/  # Celery 태스크 (stt, llm, upload, cleanup)
├── .env            # 환경변수
└── .venv/          # Python 가상환경

frontend/
├── src/routes/     # SvelteKit 페이지 (13개)
├── src/lib/components/  # Svelte 컴포넌트 (43개)
├── src/lib/stores/ # 상태관리 (9개)
└── .env            # PUBLIC_API_URL
```

---

## 운영 명령어

```bash
# 백엔드 재시작
sudo systemctl restart maxmeeting-api

# 워커 재시작
sudo systemctl restart maxmeeting-worker

# Beat 스케줄러 (녹음 파일 자동 정리)
sudo systemctl restart maxmeeting-beat

# 로그 확인
sudo journalctl -u maxmeeting-api -f      # API 로그
sudo journalctl -u maxmeeting-worker -f   # STT/LLM 워커 로그
sudo journalctl -u maxmeeting-beat -f     # Beat 스케줄러 로그

# Caddy 재시작
sudo systemctl reload caddy

# DB 접속
PGPASSWORD=password psql -h localhost -U maxmeeting -d maxmeeting
```

---

## 주요 기능

1. **회의 생성** - 안건 텍스트 → LLM 자동 파싱 (계층형)
2. **녹음** - 청크 업로드 + 실시간 파형 + 자동 STT
3. **STT** - faster-whisper (순차 처리, WebM 지원)
4. **회의록** - Gemini LLM 요약 생성 (녹음 없이도 가능)
5. **연락처** - PII 암호화 (Fernet)
6. **PWA** - 오프라인 지원, 설치 가능

---

## 최근 변경사항 (v1.16.6)

| 변경 | 설명 |
|------|------|
| STT 타임스탬프 수정 | LLM refine 비활성화로 긴 녹음 누락 문제 해결 |
| 녹음 파일 자동 정리 | 회의록 생성 3일 후 자동 삭제 (Celery Beat) |
| 디버그 코드 정리 | 프론트엔드 console.log 50+ 개 제거 |
| STT 에러 처리 | 에러 시 recording.status = FAILED 설정 |

## 이전 변경사항 (v1.16.0 ~ v1.16.5)

| 변경 | 설명 |
|------|------|
| 새 로고 | 헤더에 Gemini 나노바나나 로고 적용 |
| 인쇄용 회의록 | 2단 레이아웃, 포스트잇 메모 표시 |
| 녹음 리사이즈 | 패널 드래그 리사이즈 지원 |
| 필기 갤러리 | 스케치 백엔드 저장 및 갤러리 탭 |
| 업무배치 탭 | 메모/필기/업무배치 3탭 구조 |

## 초기 버전 (v1.0 ~ v1.3)

| 변경 | 설명 |
|------|------|
| 계층형 안건 | 3레벨 안건, 자식안건 토글 표시 |
| STT 파이프라인 | Celery 순차 처리, WebM 지원 |
| 녹음 없이 생성 | 안건/메모만으로 회의록 생성 가능 |
| PWA | 오프라인 지원, 설치 가능 |

---

## 기술 스택

| Layer | Tech |
|-------|------|
| Backend | FastAPI, SQLAlchemy 2.0, asyncpg, Celery |
| Frontend | SvelteKit 2, Svelte 5, TailwindCSS, tldraw |
| DB | PostgreSQL 16, Redis 7 |
| AI | Gemini Flash, faster-whisper |
| Infra | Caddy, systemd, Vercel |

---

## 환경변수 요약

### Backend (.env)
```bash
DATABASE_URL=postgresql+asyncpg://maxmeeting:password@localhost:5432/maxmeeting
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=<secret>
GEMINI_API_KEY=<key>
PII_ENCRYPTION_KEY=<key>
STORAGE_PATH=/data/max-meeting
```

### Frontend (.env)
```bash
PUBLIC_API_URL=https://api.meeting.etlab.kr/api/v1
```

---

## 배포 체크리스트

**⚠️ 기능 배포 시 반드시 확인:**

1. **프론트엔드 버전 업데이트** - `frontend/src/lib/version.ts`
   - `APP_VERSION` 변경 (UI에 표시됨)
   - `BUILD_DATE` 업데이트
   - 버전 히스토리 주석 추가

2. **백엔드 재시작** - `sudo systemctl restart maxmeeting-api`

3. **Git 커밋 & 푸시** - Vercel 자동 배포 트리거

---

## 코드 분석 (tldr)

코드 탐색 시 tldr CLI 활용:
```bash
tldr structure backend/app --lang python   # 코드 구조
tldr search "녹음" backend/                 # 키워드 검색
tldr impact process_recording backend/      # 함수 영향도
tldr calls backend/app/services/           # 호출 그래프
```

---

## 장애 대응

| 증상 | 조치 |
|------|------|
| 500 에러 | `journalctl -u maxmeeting-api -n 50` 로그 확인 |
| STT 안 됨 | `journalctl -u maxmeeting-worker -n 50` 워커 로그 확인 |
| CORS 에러 | FastAPI CORS 설정 확인 (Caddy는 CORS 없음) |
| 인증 실패 | JWT_SECRET 확인, 토큰 만료(60분) |
| 녹음 업로드 후 변화 없음 | 워커 로그 확인, 결과 페이지 새로고침 |
| 배포 실패 | Vercel 환경변수 PUBLIC_API_URL 확인 |
