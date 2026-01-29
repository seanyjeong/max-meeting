# MAX Meeting

AI 기반 회의 관리 플랫폼

## Features

- 회의 생성 + 안건 자동 파싱 (LLM)
- 음성 녹음 + STT 변환
- 회의록 자동 생성
- 화자 분리
- 스케치 (tldraw)

## Tech Stack

- **Backend**: FastAPI + PostgreSQL + Redis
- **Frontend**: SvelteKit 2 + Svelte 5
- **AI**: Gemini Flash + faster-whisper

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 환경변수 설정
uvicorn app.main:app --port 9000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env  # PUBLIC_API_URL 설정
npm run dev
```

## Documentation

- [CLAUDE.md](CLAUDE.md) - 전체 시스템 개요
- [docs/BACKEND.md](docs/BACKEND.md) - API 문서
- [docs/FRONTEND.md](docs/FRONTEND.md) - 프론트엔드 문서
- [docs/DATABASE.md](docs/DATABASE.md) - DB 스키마
- [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) - 인프라/배포

## License

Private
