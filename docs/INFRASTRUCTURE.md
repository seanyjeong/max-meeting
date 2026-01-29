# Infrastructure Documentation

## 서버 구성

### ET서버 (개발 서버 - 현재)

| 항목 | 값 |
|------|-----|
| **CPU** | AMD Ryzen 7 7840HS (8C/16T) |
| **RAM** | 28GB |
| **OS** | Ubuntu 24.04.3 LTS |
| **역할** | 개발 + Caddy 리버스 프록시 |

## 포트 구성

| 서비스 | 포트 | 설명 |
|--------|------|------|
| **PostgreSQL** | 5432 | maxmeeting DB |
| **Redis** | 6379 | 캐시/큐 |
| **Backend API** | 9000 | FastAPI (uvicorn) |
| **Frontend Dev** | 5173 | Vite dev server |

## Systemd 서비스

### maxmeeting-api.service

```bash
# 상태 확인
sudo systemctl status maxmeeting-api

# 재시작
sudo systemctl restart maxmeeting-api

# 로그
sudo journalctl -u maxmeeting-api -f
```

**서비스 파일 경로**: `/etc/systemd/system/maxmeeting-api.service`

```ini
[Unit]
Description=MaxMeeting FastAPI Backend
After=network.target

[Service]
Type=simple
User=et
WorkingDirectory=/home/et/max-ops/max-meeting/backend
ExecStart=/home/et/max-ops/max-meeting/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 9000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Caddy 리버스 프록시

**설정 파일**: `/etc/caddy/Caddyfile`

### api.meeting.etlab.kr

```caddyfile
api.meeting.etlab.kr {
    reverse_proxy localhost:9000
}
```

```bash
# Caddy 재시작
sudo systemctl reload caddy
```

## 프론트엔드 배포 (Vercel)

| 항목 | 값 |
|------|-----|
| **URL** | https://max-meeting.vercel.app |
| **Adapter** | @sveltejs/adapter-vercel |
| **빌드** | 자동 (git push) |
| **환경변수** | PUBLIC_API_URL=https://api.meeting.etlab.kr/api/v1 |

### Vercel 환경변수 설정

```bash
# Vercel CLI
vercel env add PUBLIC_API_URL production
# 값: https://api.meeting.etlab.kr/api/v1
```

## 데이터 경로

| 경로 | 용도 |
|------|------|
| `/home/et/max-ops/max-meeting/backend` | 백엔드 소스 |
| `/home/et/max-ops/max-meeting/frontend` | 프론트엔드 소스 |
| `/home/et/max-ops/max-meeting/data` | 저장소 (녹음, 스케치) |
| `/home/et/max-ops/max-meeting/data/recordings` | 녹음 파일 |

## CORS 설정

백엔드에서만 처리 (Caddy에서 제거함):

```python
# backend/app/core/config.py
CORS_ORIGINS = [
    "https://meeting.etlab.kr",
    "https://max-meeting.vercel.app",
    "https://*.vercel.app",
    "http://localhost:5173"
]
```

## 보안

### JWT 설정
| 항목 | 값 |
|------|-----|
| Algorithm | HS256 |
| Access Token | 60분 |
| Refresh Token | 7일 |

### Rate Limiting (Redis)
| 엔드포인트 | 제한 |
|-----------|------|
| 로그인 | 5/분 |
| 토큰 갱신 | 10/분 |
| 업로드 | 10/시간 |
| LLM 호출 | 30/시간 |

### PII 암호화
- 연락처 전화번호/이메일: Fernet 암호화 (BYTEA 저장)
- Key: `PII_ENCRYPTION_KEY` 환경변수

## 운영 명령어

```bash
# 백엔드 재시작
sudo systemctl restart maxmeeting-api

# 백엔드 로그
sudo journalctl -u maxmeeting-api -f

# Caddy 재시작
sudo systemctl reload caddy

# PostgreSQL 접속
psql -U maxmeeting -d maxmeeting

# Redis 접속
redis-cli
```

## 장애 대응

### 500 에러 발생 시
1. `sudo journalctl -u maxmeeting-api -n 50` 로그 확인
2. DB 스키마 불일치 → 컬럼 추가 (alembic 또는 직접 ALTER)
3. 서비스 재시작 `sudo systemctl restart maxmeeting-api`

### CORS 에러 발생 시
1. Caddy에 CORS 헤더 없는지 확인 (FastAPI에서만 처리)
2. `CORS_ORIGINS` 에 도메인 추가

### 토큰 인증 실패 시
1. `JWT_SECRET` 환경변수 확인
2. 토큰 만료 확인 (60분)
3. 프론트엔드 refreshToken 로직 확인
