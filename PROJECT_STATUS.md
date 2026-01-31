# MAX Meeting - 프로젝트 현황 명세

> 이 문서는 Claude가 프로젝트 상태를 빠르게 파악하기 위한 단일 참조 문서입니다.
> 마지막 업데이트: 2026-01-31

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **이름** | MAX Meeting |
| **버전** | v1.14.0 |
| **목적** | AI 기반 회의 관리 (녹음 → STT → LLM → 회의록) |
| **사용자** | 단일 사용자 내부 시스템 |
| **상태** | Production 운영 중 |

---

## 2. 기술 스택

### Backend
| 항목 | 기술 |
|------|------|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Task Queue | Celery |
| STT | faster-whisper |
| LLM | Google Gemini Flash |

### Frontend
| 항목 | 기술 |
|------|------|
| Framework | SvelteKit 2 |
| Language | Svelte 5 (runes: $state, $derived, $effect) |
| Styling | TailwindCSS |
| Drawing | Custom Canvas (SimpleSketch) |
| Deploy | Vercel |

### Infrastructure
| 항목 | 값 |
|------|-----|
| Backend Server | ET서버 (localhost:9000) |
| API Domain | https://api.meeting.etlab.kr |
| Frontend | https://max-meeting.vercel.app |
| Reverse Proxy | Caddy |
| Process Manager | systemd |

---

## 3. 핵심 기능

### 구현 완료 ✅
| 기능 | 버전 | 설명 |
|------|------|------|
| 회의 CRUD | 1.0 | 회의 생성/수정/삭제 |
| 계층형 안건 | 1.4 | 3레벨 안건 구조 (대안건 > 자식 > 손자) |
| 녹음 | 1.0 | 청크 업로드, 실시간 파형 |
| STT | 1.2 | faster-whisper, WebM 지원 |
| LLM 회의록 | 1.0 | Gemini로 요약/실행항목 생성 |
| 메모 | 1.11 | 안건별 텍스트 메모 |
| 필기 | 1.13 | Canvas 기반 스케치, PNG 저장 |
| 업무배치 | 1.11 | 회의 중 실행항목 생성 |
| 연락처 | 1.0 | PII 암호화 (Fernet) |
| PWA | 1.1 | 오프라인 지원, 설치 가능 |
| 인쇄용 회의록 | 1.3 | PDF 스타일 출력 |

### 미구현/계획 📋
| 기능 | 우선순위 | 비고 |
|------|----------|------|
| 다중 사용자 | 낮음 | 현재 단일 사용자 시스템 |
| 실시간 협업 | 낮음 | 필요 시 WebSocket |
| 모바일 앱 | 낮음 | PWA로 대체 중 |

---

## 4. 파일 구조

```
max-meeting/
├── backend/
│   ├── app/
│   │   ├── routers/       # API 엔드포인트 (11개)
│   │   │   ├── agendas.py
│   │   │   ├── auth.py
│   │   │   ├── contacts.py
│   │   │   ├── meetings.py
│   │   │   ├── notes.py
│   │   │   ├── recordings.py
│   │   │   ├── results.py
│   │   │   ├── search.py
│   │   │   └── sketches.py
│   │   ├── services/      # 비즈니스 로직 (14개)
│   │   ├── models/        # SQLAlchemy 모델 (11개)
│   │   ├── schemas/       # Pydantic 스키마
│   │   └── main.py
│   ├── workers/tasks/     # Celery 태스크
│   │   ├── stt.py         # 음성→텍스트
│   │   └── llm.py         # LLM 회의록 생성
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── routes/        # 페이지 (15개)
│   │   │   ├── +page.svelte           # 홈
│   │   │   ├── meetings/
│   │   │   │   ├── +page.svelte       # 회의 목록
│   │   │   │   ├── new/+page.svelte   # 회의 생성
│   │   │   │   └── [id]/
│   │   │   │       ├── +page.svelte   # 회의 상세
│   │   │   │       ├── record/        # 녹음 페이지
│   │   │   │       └── results/       # 결과 페이지
│   │   │   └── contacts/              # 연락처
│   │   ├── lib/
│   │   │   ├── components/  # 컴포넌트 (43개)
│   │   │   ├── stores/      # 상태관리 (16개)
│   │   │   ├── api.ts       # API 클라이언트
│   │   │   └── version.ts   # 버전 관리 ⚠️ 배포 시 필수 수정
│   │   └── app.html
│   └── .env
│
├── CLAUDE.md              # Claude 참조 문서 (배포 체크리스트 포함)
└── PROJECT_STATUS.md      # 이 파일
```

---

## 5. API 엔드포인트 요약

| 도메인 | 엔드포인트 수 | 주요 기능 |
|--------|--------------|-----------|
| /auth | 3 | 로그인, 토큰 갱신, 로그아웃 |
| /meetings | 8 | CRUD, 상태 변경, 복제 |
| /agendas | 6 | CRUD, 순서 변경, 질문 |
| /recordings | 5 | 업로드, STT 트리거, 상태 |
| /results | 7 | 회의록 생성, 실행항목 CRUD |
| /notes | 5 | 메모 CRUD |
| /sketches | 5 | 스케치 CRUD, 이미지 조회 |
| /contacts | 5 | 연락처 CRUD |
| /search | 1 | 통합 검색 |

**총 65개 엔드포인트** (모두 인증 필요)

---

## 6. 데이터베이스 스키마

### 주요 테이블
| 테이블 | 설명 | 관계 |
|--------|------|------|
| meetings | 회의 | → agendas, recordings, results |
| agendas | 안건 (계층형) | → parent_id (self), questions |
| recordings | 녹음 파일 | → meeting_id |
| results | 회의록 | → meeting_id, action_items |
| action_items | 실행 항목 | → result_id |
| segments | STT 세그먼트 | → recording_id |
| manual_notes | 메모 | → meeting_id, agenda_id |
| sketches | 스케치 | → meeting_id, agenda_id |
| contacts | 연락처 (암호화) | → meeting_attendees |

---

## 7. 코드 품질 현황

**최종 점검일**: 2026-01-31
**품질 점수**: 78/100

### 보안 ✅
- [x] XSS 방어 (DOMPurify)
- [x] SQL Injection 방어 (ORM)
- [x] 인증 (JWT, 60분 만료)
- [x] Rate Limiting (로그인 5/분, 기본 200/분)
- [x] 비밀번호 해싱 (bcrypt 12 rounds)

### 성능 ✅
- [x] N+1 쿼리 방지 (selectinload)
- [x] 지연 로딩 최적화 (lazy="noload")

### 개선 필요 ⚠️
| 항목 | 파일 | 심각도 |
|------|------|--------|
| bare exception | stt.py:180, 547 | Warning |
| any 타입 | sketch.ts:9, 16 | Warning |
| TODO 미완료 | stt.py:672 (attendee_names) | Info |

---

## 8. 배포 프로세스

### 백엔드
```bash
# 서비스 재시작
sudo systemctl restart maxmeeting-api
sudo systemctl restart maxmeeting-worker  # STT/LLM 워커

# 로그 확인
sudo journalctl -u maxmeeting-api -f
sudo journalctl -u maxmeeting-worker -f
```

### 프론트엔드
```bash
# 1. 버전 업데이트 (필수!)
# frontend/src/lib/version.ts 수정

# 2. 빌드 확인
cd frontend && npm run check && npm run build

# 3. Git push → Vercel 자동 배포
git add . && git commit -m "feat: ..." && git push origin main
```

### 배포 체크리스트 ⚠️
- [ ] `frontend/src/lib/version.ts` - APP_VERSION 업데이트
- [ ] `frontend/src/lib/version.ts` - BUILD_DATE 업데이트
- [ ] `frontend/src/lib/version.ts` - 버전 히스토리 주석 추가
- [ ] Backend 재시작 (API 변경 시)
- [ ] Worker 재시작 (STT/LLM 변경 시)

---

## 9. 환경변수

### Backend (.env)
```
DATABASE_URL=postgresql+asyncpg://maxmeeting:***@localhost:5432/maxmeeting
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=***
GEMINI_API_KEY=***
PII_ENCRYPTION_KEY=***
STORAGE_PATH=/data/max-meeting
```

### Frontend (.env)
```
PUBLIC_API_URL=https://api.meeting.etlab.kr/api/v1
```

---

## 10. 버전 히스토리

| 버전 | 날짜 | 주요 변경 |
|------|------|-----------|
| 1.14.0 | 2026-01-31 | 새 로고 및 PWA 아이콘 (Kimi AI) |
| 1.13.0 | 2026-01-31 | 필기 갤러리 탭, 스케치 백엔드 저장 |
| 1.12.0 | 2026-01-31 | 메모 포스트잇 표시 |
| 1.11.0 | 2026-01-31 | 업무배치 탭, 탭 이름 변경 |
| 1.10.0 | 2026-01-31 | 분석 완료 메시지, 버전 표시 수정 |
| 1.9.0 | 2026-01-30 | 안건 재매칭 분석 UI |
| 1.8.0 | 2026-01-30 | 질문 수정/삭제 태블릿 지원 |
| 1.7.0 | 2026-01-30 | STT 에러 처리, 드롭다운 수정 |

---

## 11. 알려진 이슈

### 해결됨 ✅
| 이슈 | 해결 버전 |
|------|-----------|
| 405 Method Not Allowed (실행항목) | 1.10.0 |
| 버전 불일치로 인한 캐시 문제 | 1.10.0 |
| 드롭다운 오버플로우 | 1.7.0 |

### 미해결 📋
| 이슈 | 심각도 | 비고 |
|------|--------|------|
| attendee_names TODO | Low | stt.py:672 |

---

## 12. 연락처

| 역할 | 담당 |
|------|------|
| 개발자 | Sean Jeong |
| AI Assistant | Claude (Anthropic) |
| Repository | github.com/seanyjeong/max-meeting |

---

*이 문서는 Claude가 세션마다 프로젝트 상태를 빠르게 파악하기 위해 유지됩니다.*
