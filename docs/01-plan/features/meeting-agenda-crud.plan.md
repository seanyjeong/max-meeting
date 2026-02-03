# Plan: 회의 중 아젠다 CRUD

> 작성일: 2026-02-03
> 상태: Draft
> 프로젝트: max-meeting

---

## 1. 개요

### 1.1 배경
현재 max-meeting에서는 회의 전에만 아젠다를 편집할 수 있습니다. 회의 진행 중 새로운 논의 사항이 생기거나, 기존 아젠다를 수정해야 할 때 대응이 불가능합니다.

### 1.2 목표
회의 녹음 중에도 안전하게 아젠다를 추가/수정/삭제할 수 있는 기능을 제공합니다.

### 1.3 범위

**포함:**
- 회의 중 새 아젠다 추가 (Create)
- 아젠다 제목/설명 인라인 편집 (Update)
- 아젠다 삭제 - 조건부 (Delete)
- 녹음 상태별 권한 제어

**제외:**
- 회의 중 아젠다 순서 변경 (위험도 높음)
- 다중 사용자 동시 편집 (향후 과제)
- WebSocket 실시간 동기화 (현재 SSE만 사용)

---

## 2. 현황 분석

### 2.1 기존 시스템

| 컴포넌트 | 역할 | CRUD 상태 |
|---------|------|----------|
| `AgendaEditor.svelte` | 회의 전 아젠다 편집 | 전체 CRUD |
| `AgendaNotePanel.svelte` | 회의 중 아젠다 표시 + 메모 | Read Only |
| `AgendaTracker.svelte` | 진행 추적 (레거시) | Read Only |

### 2.2 데이터 구조

```typescript
interface Agenda {
  id: number;                    // Backend ID
  meeting_id: number;
  parent_id: number | null;      // 계층형 지원
  level: number;                 // 1-3
  order_num: number;
  title: string;
  description: string | null;
  status: 'pending' | 'in_progress' | 'completed';
  time_segments: TimeSegment[];  // 녹음 구간
  started_at_seconds: number | null;
  questions: AgendaQuestion[];
  children?: Agenda[];
}

interface TimeSegment {
  start: number;
  end: number | null;  // null = 현재 녹음 중
}
```

### 2.3 API 현황

| Endpoint | Method | 용도 |
|----------|--------|------|
| `/meetings/{id}/agendas` | POST | 아젠다 생성 |
| `/agendas/{id}` | PATCH | 아젠다 수정 |
| `/agendas/{id}` | DELETE | 아젠다 삭제 (soft) |

---

## 3. 요구사항

### 3.1 기능 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|----------|
| FR-01 | 녹음 전/후에는 전체 CRUD 가능 | Must |
| FR-02 | 녹음 중 새 아젠다 추가 (목록 끝에만) | Must |
| FR-03 | 녹음 중 비활성 아젠다 제목/설명 편집 | Must |
| FR-04 | 현재 녹음 중인 아젠다는 편집 불가 | Must |
| FR-05 | time_segments 있는 아젠다 삭제 금지 | Must |
| FR-06 | 편집 권한에 따른 UI 피드백 (잠금 아이콘 등) | Should |

### 3.2 비기능 요구사항

| ID | 요구사항 | 측정 기준 |
|----|---------|----------|
| NFR-01 | 기존 녹음 기능에 영향 없음 | 기존 테스트 통과 |
| NFR-02 | time_segments 데이터 무결성 보장 | 편집 후 녹음 구간 유지 |
| NFR-03 | 낙관적 업데이트 + 롤백 | API 실패 시 원복 |

---

## 4. 기술 접근 방식

### 4.1 상태별 권한 매트릭스

| 녹음 상태 | Create | Update | Delete | 비고 |
|----------|--------|--------|--------|------|
| 녹음 전 | O | O | O | 전체 CRUD |
| 녹음 중 | △ (끝에만) | △ (비활성만) | X | 제한적 |
| 일시정지 | O | O | △ | time_segments 없는 것만 삭제 |
| 녹음 후 | O | O | △ | time_segments 없는 것만 삭제 |

### 4.2 보호 로직

```
1. activeAgendaId === agenda.id → 모든 편집 금지
2. time_segments에 end: null 존재 → 모든 편집 금지
3. time_segments.length > 0 → 삭제만 금지
```

### 4.3 컴포넌트 전략

**기존 AgendaNotePanel 확장** (새 컴포넌트 X)
- `editMode` prop 추가
- 인라인 편집 UI 추가
- 권한 체크 로직 통합

---

## 5. 구현 계획

### 5.1 파일 변경 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `frontend/src/lib/utils/agenda-permissions.ts` | 신규 | 권한 체크 유틸리티 |
| `frontend/src/lib/components/recording/AgendaNotePanel.svelte` | 수정 | CRUD UI 추가 |
| `frontend/src/routes/meetings/[id]/record/+page.svelte` | 수정 | 핸들러 + props |

### 5.2 구현 순서

1. **agenda-permissions.ts** 생성 - 권한 로직 분리
2. **AgendaNotePanel** Props 확장 - editMode, activeAgendaId 등
3. **인라인 편집 UI** - 제목 클릭 → input 전환
4. **추가 버튼** - 목록 하단에 "+ 안건 추가"
5. **삭제 기능** - 권한 있는 경우만 표시
6. **record/+page.svelte** 연결 - 핸들러 구현 + props 전달

---

## 6. 위험 요소 및 대응

| 위험 | 영향 | 대응 방안 |
|------|------|----------|
| 녹음 중 activeAgenda 삭제 시 time_segments 깨짐 | 높음 | activeAgendaId 체크로 원천 차단 |
| API 실패 시 UI 불일치 | 중간 | 낙관적 업데이트 + 롤백 |
| 계층형 아젠다 처리 누락 | 중간 | children 배열에도 동일 로직 적용 |

---

## 7. 성공 기준

- [ ] 녹음 전/후 전체 CRUD 정상 작동
- [ ] 녹음 중 제한적 편집 정상 작동
- [ ] 현재 녹음 중 아젠다 편집 차단 확인
- [ ] time_segments 있는 아젠다 삭제 차단 확인
- [ ] 기존 녹음 → 결과 페이지 플로우 정상 작동
