# Backend API Documentation

## 서버 정보

| 항목 | 값 |
|------|-----|
| **Framework** | FastAPI |
| **Port** | 9000 |
| **Base URL** | `/api/v1` |
| **Systemd** | `maxmeeting-api.service` |
| **Working Dir** | `/home/et/max-ops/max-meeting/backend` |
| **Python** | 3.12 (venv: `.venv`) |

## API 엔드포인트 (46개)

### Auth (4)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/auth/login` | 비밀번호 로그인 |
| POST | `/auth/refresh` | 토큰 갱신 |
| POST | `/auth/logout` | 로그아웃 |
| GET | `/auth/me` | 현재 사용자 |

### Meetings (9)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/meetings` | 목록 (paginated, filters) |
| POST | `/meetings` | 생성 |
| GET | `/meetings/{id}` | 상세 |
| PATCH | `/meetings/{id}` | 수정 |
| DELETE | `/meetings/{id}` | 삭제 (soft) |
| POST | `/meetings/{id}/restore` | 복원 |
| POST | `/meetings/{id}/attendees` | 참석자 추가 |
| DELETE | `/meetings/{id}/attendees/{contact_id}` | 참석자 제거 |

### Meeting Types (3)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/meeting-types` | 목록 |
| POST | `/meeting-types` | 생성 |
| DELETE | `/meeting-types/{id}` | 삭제 |

### Agendas (12)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/meetings/{id}/agendas` | 목록 (계층형) |
| POST | `/meetings/{id}/agendas` | 생성 |
| POST | `/meetings/{id}/agendas/batch` | 일괄 생성 |
| POST | `/meetings/{id}/agendas/parse` | LLM 파싱 |
| GET | `/agendas/{id}` | 상세 |
| PATCH | `/agendas/{id}` | 수정 |
| DELETE | `/agendas/{id}` | 삭제 |
| POST | `/agendas/{id}/reorder` | 순서 변경 |
| POST | `/agendas/{id}/move` | 부모 이동 |
| POST | `/agendas/{id}/questions/generate` | 질문 생성 |
| PATCH | `/questions/{id}` | 질문 수정 |
| DELETE | `/questions/{id}` | 질문 삭제 |

### Recordings (5)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/recordings/init` | 업로드 초기화 |
| POST | `/recordings/{id}/upload` | 청크 업로드 |
| GET | `/recordings/{id}` | 상세 |
| GET | `/recordings/{id}/progress` | 진행률 |
| DELETE | `/recordings/{id}` | 삭제 |

### Results (8)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/meetings/{id}/results` | 결과 버전 목록 |
| POST | `/meetings/{id}/results/generate` | 요약 생성 |
| GET | `/results/{id}` | 결과 상세 |
| PATCH | `/results/{id}` | 결과 수정 |
| POST | `/results/{id}/verify` | 검증 완료 |
| POST | `/results/{id}/regenerate` | 재생성 |
| GET | `/meetings/{id}/action-items` | 액션아이템 |
| POST | `/meetings/{id}/action-items` | 액션아이템 생성 |

### Contacts (5)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/contacts` | 목록 |
| POST | `/contacts` | 생성 |
| GET | `/contacts/{id}` | 상세 |
| PATCH | `/contacts/{id}` | 수정 |
| DELETE | `/contacts/{id}` | 삭제 |

### Notes & Sketches (6)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/meetings/{id}/notes` | 노트 목록 |
| POST | `/meetings/{id}/notes` | 노트 생성 |
| PATCH | `/notes/{id}` | 노트 수정 |
| DELETE | `/notes/{id}` | 노트 삭제 |
| GET | `/sketches/{id}/export` | 스케치 내보내기 |

### Search (1)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/search` | 전문 검색 (pg_trgm) |

## 서비스 구조

```
app/
├── api/v1/           # 라우터
│   ├── auth.py
│   ├── meetings.py
│   ├── agendas.py
│   ├── recordings.py
│   ├── results.py
│   ├── contacts.py
│   ├── notes.py
│   ├── sketches.py
│   └── search.py
├── models/           # SQLAlchemy 모델
├── services/         # 비즈니스 로직
│   ├── llm.py        # Gemini LLM
│   ├── stt.py        # faster-whisper
│   └── encryption.py # PII 암호화
├── core/
│   ├── config.py     # Settings
│   ├── security.py   # JWT
│   └── deps.py       # 의존성
└── workers/          # Celery 태스크
```

## 환경변수 (주요)

```bash
# DB
DATABASE_URL=postgresql+asyncpg://maxmeeting:password@localhost:5432/maxmeeting

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=<secret>
JWT_ACCESS_EXPIRE_MINUTES=60
JWT_REFRESH_EXPIRE_DAYS=7

# LLM
GEMINI_API_KEY=<key>

# Storage
STORAGE_PATH=/home/et/max-ops/max-meeting/data

# PII
PII_ENCRYPTION_KEY=<key>
```

## Rate Limiting

| 엔드포인트 | 제한 |
|-----------|------|
| `/auth/login` | 5/min |
| `/auth/refresh` | 10/min |
| 업로드 | 10/hour |
| LLM 호출 | 30/hour |
| 기본 | 200/min |
