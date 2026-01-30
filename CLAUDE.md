# MAX Meeting - AI 회의 관리 시스템

> 음성 녹음 → STT → LLM 분석 → 회의록 자동 생성

## Quick Reference

| 구분 | 값 |
|------|-----|
| **Version** | v1.2.0 (2026-01-30) |
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
├── workers/tasks/  # Celery 태스크 (stt, llm, upload)
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

# 로그 확인
sudo journalctl -u maxmeeting-api -f      # API 로그
sudo journalctl -u maxmeeting-worker -f   # STT/LLM 워커 로그

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

## 최근 변경사항 (v1.2.0)

| 변경 | 설명 |
|------|------|
| STT 파이프라인 | Celery chord → 순차 처리 (temp 파일 문제 해결) |
| WebM 지원 | ffmpeg fallback으로 duration 감지 |
| 녹음 없이 생성 | 안건/메모만으로 회의록 생성 가능 |
| UI 용어 | "전사록" → "대화 내용" |
| 상태 폴링 | 자동 업데이트 + 토스트 알림 |
| 성능 개선 | SQLAlchemy lazy="noload" (15초 → 100ms) |

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
