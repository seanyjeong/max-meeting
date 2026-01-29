# MAX Meeting - AI 회의 관리 시스템

> 음성 녹음 → STT → LLM 분석 → 회의록 자동 생성

## Quick Reference

| 구분 | 값 |
|------|-----|
| **Backend** | FastAPI @ `localhost:9000` |
| **Frontend** | SvelteKit @ Vercel (`max-meeting.vercel.app`) |
| **DB** | PostgreSQL @ `localhost:5432/maxmeeting` |
| **API Base** | `https://api.meeting.etlab.kr/api/v1` |

## 상세 문서

| 문서 | 내용 |
|------|------|
| [docs/BACKEND.md](docs/BACKEND.md) | API 46개, 서비스 구조, 환경변수 |
| [docs/FRONTEND.md](docs/FRONTEND.md) | 라우트 13개, 컴포넌트 26개, 스토어 8개 |
| [docs/DATABASE.md](docs/DATABASE.md) | 테이블 17개, 스키마, 관계도 |
| [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) | 서버, 포트, systemd, Caddy, 배포 |

---

## 핵심 경로

```
backend/
├── app/api/v1/     # API 라우터
├── app/models/     # SQLAlchemy 모델
├── app/services/   # 비즈니스 로직 (llm.py, stt.py)
├── .env            # 환경변수
└── .venv/          # Python 가상환경

frontend/
├── src/routes/     # SvelteKit 페이지
├── src/lib/components/  # Svelte 컴포넌트
├── src/lib/stores/ # 상태관리
└── .env            # PUBLIC_API_URL
```

---

## 운영 명령어

```bash
# 백엔드 재시작
sudo systemctl restart maxmeeting-api

# 백엔드 로그
sudo journalctl -u maxmeeting-api -f

# Caddy 재시작
sudo systemctl reload caddy

# DB 접속
psql -U maxmeeting -d maxmeeting
```

---

## 주요 기능

1. **회의 생성** - 안건 텍스트 → LLM 자동 파싱 (계층형)
2. **녹음** - 청크 업로드 + 실시간 파형
3. **STT** - faster-whisper + 화자분리
4. **회의록** - Gemini LLM 요약 생성
5. **연락처** - PII 암호화 (Fernet)

---

## 기술 스택

| Layer | Tech |
|-------|------|
| Backend | FastAPI, SQLAlchemy, asyncpg, Celery |
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
STORAGE_PATH=/home/et/max-ops/max-meeting/data
```

### Frontend (.env)
```bash
PUBLIC_API_URL=https://api.meeting.etlab.kr/api/v1
```

---

## 장애 대응

| 증상 | 조치 |
|------|------|
| 500 에러 | `journalctl -u maxmeeting-api -n 50` 로그 확인 → DB 스키마 불일치 시 ALTER |
| CORS 에러 | Caddy 아닌 FastAPI에서만 CORS 처리 확인 |
| 인증 실패 | JWT_SECRET 확인, 토큰 만료(60분) 확인 |
| 배포 실패 | Vercel 환경변수 PUBLIC_API_URL 확인 |
