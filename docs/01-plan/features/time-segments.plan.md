# Plan: 안건별 다중 시간 구간 (time-segments)

> 생성일: 2026-01-30
> 상태: Draft

## 1. 개요

### 1.1 문제 정의

현재 시스템은 안건(Agenda)당 **하나의 시작 시간**(`started_at_seconds`)만 저장합니다.
회의 중 안건을 왔다갔다 하면 나중에 다시 논의한 내용이 **다른 안건에 잘못 포함**됩니다.

**현재 동작 (문제):**
```
녹음 시작 → 안건1 (0초)
안건2로 이동 → 안건2 (30초)
안건3으로 이동 → 안건3 (60초)
다시 안건1로 → 안건1은 이미 0초 있으므로 변경 없음
└→ 결과: 60-80초 대화가 안건3에 포함됨 (실제로는 안건1 논의)
```

### 1.2 목표

- 안건 전환을 **여러 번 기록**하여 왔다갔다 하는 회의 지원
- 각 안건에 해당하는 대화 내용만 정확히 추출
- 결과 페이지에서 안건별 대화 탭으로 분리 표시

### 1.3 기대 효과

| 항목 | Before | After |
|------|--------|-------|
| 안건1 대화 | 0-30초만 | 0-30초 + 60-80초 |
| 대화 정확도 | 순차적 회의만 정확 | 왔다갔다 회의도 정확 |
| UI | 전체 대화 한 덩어리 | 안건별 탭 분리 |

## 2. 요구사항

### 2.1 기능 요구사항

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-01 | 안건 전환 시 이전 안건 종료 시간 + 새 안건 시작 시간 기록 | P0 |
| FR-02 | 하나의 안건이 여러 시간 구간 가질 수 있음 | P0 |
| FR-03 | LLM 처리 시 여러 구간 합쳐서 transcript 추출 | P0 |
| FR-04 | 결과 페이지에서 안건별 대화 탭 UI | P1 |
| FR-05 | 기존 started_at_seconds와 하위 호환 | P0 |

### 2.2 비기능 요구사항

| ID | 요구사항 | 기준 |
|----|----------|------|
| NFR-01 | DB 마이그레이션 안전 | 기존 데이터 유지 |
| NFR-02 | API 응답 시간 | < 200ms |
| NFR-03 | 프론트엔드 반응성 | 즉각적 UI 업데이트 |

## 3. 데이터 모델

### 3.1 time_segments 구조

```json
// Agenda.time_segments (JSON array)
[
  {"start": 0, "end": 30},     // 첫 번째 구간
  {"start": 60, "end": 80}     // 두 번째 구간 (다시 돌아와서 논의)
]
```

### 3.2 DB 변경

```sql
-- 새 컬럼 추가 (nullable, 기존 데이터 영향 없음)
ALTER TABLE agendas ADD COLUMN time_segments JSONB DEFAULT NULL;
```

### 3.3 하위 호환성

- `started_at_seconds` 유지 (첫 번째 시작 시간 = time_segments[0].start)
- `time_segments` 없으면 기존 로직 사용
- `time_segments` 있으면 여러 구간 합산

## 4. 변경 범위

### 4.1 Backend

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/models/agenda.py` | `time_segments` 컬럼 추가 |
| `backend/app/schemas/agenda.py` | `time_segments` 필드 추가 |
| `backend/app/routers/meetings.py` | time_segments 저장 API |
| `backend/workers/tasks/llm.py` | 여러 구간 합쳐서 transcript 추출 |
| `alembic/versions/xxx_add_time_segments.py` | DB 마이그레이션 |

### 4.2 Frontend

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/lib/stores/meeting.ts` | Agenda 타입에 time_segments 추가 |
| `frontend/src/lib/components/recording/AgendaNotePanel.svelte` | 안건 전환 시 이전 안건 end 기록 |
| `frontend/src/routes/meetings/[id]/record/+page.svelte` | time_segments 저장 로직 |
| `frontend/src/routes/meetings/[id]/results/+page.svelte` | 안건별 대화 탭 UI |

## 5. 구현 순서

```
1. [Backend] DB 마이그레이션 - time_segments 컬럼 추가
2. [Backend] 모델/스키마 수정
3. [Backend] API 수정 - time_segments 저장
4. [Frontend] 타입 수정
5. [Frontend] 안건 전환 로직 수정 (핵심)
6. [Backend] LLM 처리 수정 - 여러 구간 합산
7. [Frontend] 결과 페이지 탭 UI
8. 테스트 및 배포
```

## 6. 위험 요소

| 위험 | 영향 | 완화 방안 |
|------|------|----------|
| DB 마이그레이션 실패 | 서비스 중단 | nullable 컬럼, 롤백 스크립트 준비 |
| 기존 데이터 호환성 | 이전 회의 오류 | time_segments 없으면 기존 로직 유지 |
| 복잡한 UI 상태 관리 | 버그 가능성 | 상태 전환 로직 단순화 |

## 7. 성공 기준

- [ ] 안건 왔다갔다 시 모든 구간 정확히 기록
- [ ] LLM 결과에 해당 안건 대화만 포함
- [ ] 결과 페이지에서 안건별 탭으로 대화 분리
- [ ] 기존 회의 데이터 정상 작동

---

## 다음 단계

`/pdca design time-segments` 실행하여 상세 설계 진행
