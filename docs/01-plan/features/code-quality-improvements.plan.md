# Code Quality Improvements Plan

> MAX Meeting 코드 품질 개선 계획

## 메타 정보

| 항목 | 값 |
|------|-----|
| **Feature** | code-quality-improvements |
| **Version** | v1.6.0 |
| **Created** | 2026-01-30 |
| **Author** | Claude Code |
| **Status** | Draft |
| **Priority** | High |

---

## 1. 배경 및 목적

### 1.1 현재 상황
- Backend 품질 점수: 78/100
- Frontend 품질 점수: 72/100
- Critical 이슈 6개, Important 이슈 12개+ 발견

### 1.2 개선 목적
- 보안 취약점 제거 (SQL Injection, 토큰 저장 방식)
- 코드 유지보수성 향상 (중복 제거, 파일 분할)
- 성능 및 안정성 개선 (deprecated API 교체)

---

## 2. 범위

### 2.1 In Scope

#### Phase 1: Critical 보안 이슈 (즉시)
| # | 영역 | 파일 | 이슈 | 작업 |
|---|------|------|------|------|
| 1 | BE | `services/contact.py:48` | SQL Injection | LIKE 패턴 이스케이프 |
| 2 | BE | `workers/tasks/stt.py` | Deprecated asyncio | `asyncio.run()` 사용 |
| 3 | BE | `workers/tasks/llm.py` | Deprecated asyncio | `asyncio.run()` 사용 |
| 4 | BE | `routers/results.py:232-303` | 소유권 검증 없음 | 서비스 레이어 분리 + 검증 추가 |
| 5 | FE | `lib/api.ts:131` | API 응답 로깅 | 프로덕션 로그 제거 |
| 6 | FE | `stores/auth.ts` | localStorage 토큰 | 보안 검토 (문서화 또는 개선) |

#### Phase 2: 코드 품질 개선 (단기)
| # | 영역 | 작업 | 파일 |
|---|------|------|------|
| 7 | FE | formatDate/formatTime 통합 | 9개 → 1개 유틸리티 |
| 8 | FE | 대형 파일 분할 | results/+page.svelte (1063줄) |
| 9 | FE | 대형 파일 분할 | [id]/+page.svelte (689줄) |
| 10 | FE | console.log 정리 | 26개 파일, 136개 로그 |
| 11 | BE | 중복 코드 제거 | agendas.py 질문 생성 로직 |
| 12 | BE | 서비스 레이어 분리 | meetings.py:391-444 |

#### Phase 3: 아키텍처 개선 (중기)
| # | 영역 | 작업 | 설명 |
|---|------|------|------|
| 13 | BE | 프롬프트 외부화 | llm.py → prompts/*.yaml |
| 14 | BE | 함수 분할 | stt.py, llm.py 대형 함수 |
| 15 | FE | 에러 처리 통합 | 중앙화된 에러 유틸리티 |
| 16 | FE | any 타입 제거 | unknown + 타입 가드 |

### 2.2 Out of Scope
- WebSocket/SSE 전환 (별도 feature로 분리)
- 테스트 커버리지 확대 (별도 feature로 분리)
- UI/UX 개선 (별도 feature로 분리)

---

## 3. 성공 기준

| 지표 | 현재 | 목표 |
|------|------|------|
| Backend 품질 점수 | 78/100 | 90/100 |
| Frontend 품질 점수 | 72/100 | 85/100 |
| Critical 이슈 | 6개 | 0개 |
| Important 이슈 | 12개+ | 5개 이하 |
| 중복 코드 | formatDate 9개 | 1개 |
| 최대 파일 줄 수 | 1063줄 | 400줄 이하 |

---

## 4. 작업 분류

### 4.1 Phase 1: Critical (예상 작업량: 소)

```
[x] 1. SQL Injection 수정
    - contact.py LIKE 패턴 이스케이프

[x] 2. Deprecated asyncio 교체
    - stt.py: asyncio.run() 사용
    - llm.py: asyncio.run() 사용

[x] 3. 소유권 검증 추가
    - results.py → ResultService 분리
    - meeting_id 소유권 검증 미들웨어

[x] 4. 프로덕션 로그 정리
    - api.ts 응답 로깅 조건부 처리
    - 환경변수 기반 로그 레벨

[x] 5. 토큰 저장 방식 문서화
    - 현재 방식의 위험성 문서화
    - 또는 메모리 저장으로 변경
```

### 4.2 Phase 2: Important (예상 작업량: 중)

```
[ ] 6. 유틸리티 함수 통합
    - $lib/utils/format.ts 생성
    - formatDate, formatTime, truncate 이동
    - 기존 9개 파일 import 변경

[ ] 7. results/+page.svelte 분할
    - StatusSection.svelte
    - HeaderSection.svelte
    - FilterSection.svelte
    - ContentSection.svelte

[ ] 8. [id]/+page.svelte 분할
    - AgendaList.svelte
    - QuestionEditor.svelte
    - ParticipantSection.svelte

[ ] 9. console.log 정리
    - 개발용 로그 → debug 유틸리티
    - 프로덕션 빌드 시 제거

[ ] 10. Backend 중복 제거
    - _generate_questions_for_agenda() 추출
    - meetings.py → MeetingService 분리
```

### 4.3 Phase 3: Architecture (예상 작업량: 대)

```
[ ] 11. 프롬프트 외부화
    - prompts/meeting_summary.yaml
    - prompts/agenda_parsing.yaml
    - PromptLoader 유틸리티

[ ] 12. 대형 함수 분할
    - process_recording → 3개 함수
    - generate_meeting_result → 3개 함수

[ ] 13. 에러 처리 통합
    - $lib/utils/error.ts
    - handleApiError() 유틸리티
    - 타입 가드 함수

[ ] 14. 타입 안전성 강화
    - any → unknown 변경
    - 타입 가드 함수 추가
```

---

## 5. 의존성

```
Phase 1 (Critical)
    ↓ (완료 후)
Phase 2 (Important)
    ↓ (완료 후)
Phase 3 (Architecture)
```

- Phase 1은 독립적으로 진행 가능
- Phase 2의 파일 분할은 Phase 1 완료 후 진행 권장
- Phase 3은 Phase 2 완료 후 진행

---

## 6. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 파일 분할 시 import 누락 | 빌드 실패 | 단계별 테스트 |
| asyncio 변경 시 동작 변경 | 워커 오류 | 로컬 테스트 후 배포 |
| 유틸리티 통합 시 타입 불일치 | 런타임 에러 | TypeScript strict 모드 |

---

## 7. 검증 계획

### Phase 1 검증
- [ ] SQL Injection 테스트 (특수문자 입력)
- [ ] STT 워커 정상 동작 확인
- [ ] LLM 워커 정상 동작 확인
- [ ] 프로덕션 빌드 로그 확인

### Phase 2 검증
- [ ] 모든 페이지 정상 렌더링
- [ ] 컴포넌트 props 전달 확인
- [ ] 빌드 성공 확인

### Phase 3 검증
- [ ] 프롬프트 로딩 테스트
- [ ] 에러 처리 동작 확인
- [ ] 타입 체크 통과

---

## 8. 다음 단계

1. **Plan 승인** → `/pdca design code-quality-improvements`
2. **Design 작성** → 상세 구현 명세
3. **Do 실행** → Phase별 구현
4. **Check 분석** → Gap 분석으로 검증

---

## Changelog

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-01-30 | 0.1 | 초안 작성 (코드 리뷰 기반) |
