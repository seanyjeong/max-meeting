# Design: 회의 중 아젠다 CRUD

> 작성일: 2026-02-03
> Plan 문서: `docs/01-plan/features/meeting-agenda-crud.plan.md`
> 상태: Draft

---

## 1. 아키텍처 개요

### 1.1 컴포넌트 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    record/+page.svelte                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ State: meeting, activeAgendaId, isRecording, isPaused│   │
│  │ Handlers: handleAgendaCreate/Update/Delete          │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │ props                            │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              AgendaNotePanel.svelte                  │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │ agenda-permissions.ts                        │    │   │
│  │  │ getAgendaPermissions(agenda, activeId, rec) │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │                                                      │   │
│  │  [Agenda List]  ←→  [Inline Edit UI]                │   │
│  │  [Add Button]   ←→  [Delete Button]                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ API calls
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                        │
│  POST /meetings/{id}/agendas                                │
│  PATCH /agendas/{id}                                        │
│  DELETE /agendas/{id}                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 상세 설계

### 2.1 agenda-permissions.ts (신규)

**경로:** `frontend/src/lib/utils/agenda-permissions.ts`

```typescript
import type { Agenda } from '$lib/stores/meeting';

export interface AgendaPermissions {
  canEditTitle: boolean;
  canEditDescription: boolean;
  canDelete: boolean;
  canAddChild: boolean;
  reason?: string;
}

/**
 * 아젠다의 편집 권한을 계산합니다.
 *
 * @param agenda - 대상 아젠다
 * @param activeAgendaId - 현재 녹음 중인 아젠다 ID (null = 녹음 안함)
 * @param isRecording - 녹음 진행 중 여부
 * @returns 권한 객체
 */
export function getAgendaPermissions(
  agenda: Agenda,
  activeAgendaId: number | null,
  isRecording: boolean
): AgendaPermissions {
  // 열린 세그먼트 체크 (end: null = 현재 녹음 중)
  const hasOpenSegment = agenda.time_segments?.some(s => s.end === null) ?? false;
  // 녹음된 구간 존재 여부
  const hasAnySegment = (agenda.time_segments?.length ?? 0) > 0;

  // Case 1: 현재 녹음 중인 아젠다 또는 열린 세그먼트 존재
  if (activeAgendaId === agenda.id || hasOpenSegment) {
    return {
      canEditTitle: false,
      canEditDescription: false,
      canDelete: false,
      canAddChild: false,
      reason: '현재 녹음 중인 안건입니다'
    };
  }

  // Case 2: 녹음 중이고, 이미 녹음된 구간이 있음
  if (isRecording && hasAnySegment) {
    return {
      canEditTitle: true,
      canEditDescription: true,
      canDelete: false,
      canAddChild: false,
      reason: '녹음된 구간이 있어 삭제할 수 없습니다'
    };
  }

  // Case 3: 녹음 중이지만 녹음된 구간 없음
  if (isRecording) {
    return {
      canEditTitle: true,
      canEditDescription: true,
      canDelete: true,
      canAddChild: false  // 녹음 중에는 자식 추가 비허용
    };
  }

  // Case 4: 녹음 중 아님 - time_segments 유무에 따라
  return {
    canEditTitle: true,
    canEditDescription: true,
    canDelete: !hasAnySegment,
    canAddChild: true
  };
}

/**
 * 새 아젠다 추가 가능 여부
 */
export function canAddAgenda(isRecording: boolean, isPaused: boolean): boolean {
  // 녹음 중이 아니거나, 일시정지 상태면 추가 가능
  return !isRecording || isPaused;
}
```

---

### 2.2 AgendaNotePanel.svelte 수정

**경로:** `frontend/src/lib/components/recording/AgendaNotePanel.svelte`

#### 2.2.1 Props 확장

```typescript
interface Props {
  // 기존 props
  agendas: Agenda[];
  currentAgendaIndex: number;
  notes: Map<number, string>;
  recordingTime: number;
  isRecording: boolean;
  onAgendaChange: (prevId: number | null, newId: number, time: number) => void;
  onChildAgendaChange?: (prevId: number | null, childId: number, time: number) => void;
  onQuestionToggle: (questionId: number, answered: boolean) => void;
  onNoteChange: (agendaId: number, content: string) => void;

  // 신규 props
  activeAgendaId?: number | null;
  isPaused?: boolean;
  onAgendaCreate?: (title: string, parentId?: number) => Promise<void>;
  onAgendaUpdate?: (id: number, data: { title?: string; description?: string }) => Promise<void>;
  onAgendaDelete?: (id: number) => Promise<void>;
}
```

#### 2.2.2 내부 상태

```typescript
// 인라인 편집 상태
let editingAgendaId = $state<number | null>(null);
let editingField = $state<'title' | 'description' | null>(null);
let editValue = $state('');

// 새 안건 추가 UI 상태
let showAddForm = $state(false);
let newAgendaTitle = $state('');
```

#### 2.2.3 UI 변경사항

**1. 아젠다 목록 아이템 (인라인 편집)**

```svelte
{#each agendas as agenda, index (agenda.id)}
  {@const perm = getAgendaPermissions(agenda, activeAgendaId, isRecording)}

  <div class="agenda-item ...">
    <!-- 제목 영역 -->
    {#if editingAgendaId === agenda.id && editingField === 'title'}
      <!-- 편집 모드 -->
      <input
        type="text"
        bind:value={editValue}
        onblur={() => handleSaveEdit(agenda.id)}
        onkeydown={(e) => e.key === 'Enter' && handleSaveEdit(agenda.id)}
        class="flex-1 px-2 py-1 border rounded text-sm"
        autofocus
      />
    {:else}
      <!-- 표시 모드 -->
      <button
        onclick={() => perm.canEditTitle && startEdit(agenda.id, 'title', agenda.title)}
        class="flex-1 text-left truncate {perm.canEditTitle ? 'hover:bg-gray-100 cursor-text' : 'cursor-default'}"
        disabled={!perm.canEditTitle}
      >
        {agenda.order_num}. {agenda.title}
      </button>

      <!-- 잠금 아이콘 (편집 불가 시) -->
      {#if !perm.canEditTitle}
        <span class="text-gray-400" title={perm.reason}>
          <svg class="w-4 h-4"><!-- 잠금 아이콘 --></svg>
        </span>
      {/if}
    {/if}

    <!-- 삭제 버튼 -->
    {#if perm.canDelete && onAgendaDelete}
      <button
        onclick={() => handleDelete(agenda.id)}
        class="p-1 text-red-500 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100"
        title="안건 삭제"
      >
        <svg class="w-4 h-4"><!-- 삭제 아이콘 --></svg>
      </button>
    {/if}
  </div>
{/each}
```

**2. 안건 추가 버튼 (목록 하단)**

```svelte
<!-- 안건 목록 끝에 추가 -->
{#if canAddAgenda(isRecording, isPaused ?? false) && onAgendaCreate}
  {#if showAddForm}
    <div class="p-2 border-t">
      <input
        type="text"
        bind:value={newAgendaTitle}
        placeholder="새 안건 제목..."
        class="w-full px-3 py-2 border rounded text-sm"
        onkeydown={(e) => e.key === 'Enter' && handleAddAgenda()}
        autofocus
      />
      <div class="flex gap-2 mt-2">
        <button onclick={handleAddAgenda} class="btn-primary text-sm">추가</button>
        <button onclick={() => showAddForm = false} class="btn-secondary text-sm">취소</button>
      </div>
    </div>
  {:else}
    <button
      onclick={() => showAddForm = true}
      class="w-full p-3 text-sm text-blue-600 hover:bg-blue-50 flex items-center justify-center gap-2"
    >
      <svg class="w-4 h-4"><!-- 플러스 아이콘 --></svg>
      안건 추가
    </button>
  {/if}
{/if}
```

#### 2.2.4 핸들러 함수

```typescript
// 인라인 편집 시작
function startEdit(agendaId: number, field: 'title' | 'description', currentValue: string) {
  editingAgendaId = agendaId;
  editingField = field;
  editValue = currentValue;
}

// 편집 저장
async function handleSaveEdit(agendaId: number) {
  if (!onAgendaUpdate || !editingField) return;

  const data = editingField === 'title'
    ? { title: editValue.trim() }
    : { description: editValue.trim() };

  if (data.title === '' && editingField === 'title') {
    // 빈 제목 불허
    editingAgendaId = null;
    editingField = null;
    return;
  }

  await onAgendaUpdate(agendaId, data);
  editingAgendaId = null;
  editingField = null;
}

// 안건 추가
async function handleAddAgenda() {
  if (!onAgendaCreate || !newAgendaTitle.trim()) return;

  await onAgendaCreate(newAgendaTitle.trim());
  newAgendaTitle = '';
  showAddForm = false;
}

// 안건 삭제
async function handleDelete(agendaId: number) {
  if (!onAgendaDelete) return;

  // 확인 없이 바로 삭제 (권한 체크는 이미 됨)
  await onAgendaDelete(agendaId);
}
```

---

### 2.3 record/+page.svelte 수정

**경로:** `frontend/src/routes/meetings/[id]/record/+page.svelte`

#### 2.3.1 핸들러 추가

```typescript
// 안건 생성
async function handleAgendaCreate(title: string, parentId?: number) {
  if (!meeting) return;

  try {
    const response = await api.post<Agenda>(`/meetings/${meetingId}/agendas`, {
      title,
      parent_id: parentId ?? null,
      order_num: meeting.agendas.length + 1
    });

    // 로컬 상태 업데이트
    meeting = {
      ...meeting,
      agendas: [...meeting.agendas, response]
    };

    toast.success('안건이 추가되었습니다');
  } catch (error) {
    toast.error('안건 추가에 실패했습니다');
  }
}

// 안건 수정 (낙관적 업데이트)
async function handleAgendaUpdate(id: number, data: { title?: string; description?: string }) {
  if (!meeting) return;

  const oldAgenda = findAgendaById(id);
  if (!oldAgenda) return;

  // 낙관적 업데이트
  updateLocalAgenda(id, data);

  try {
    await api.patch(`/agendas/${id}`, data);
  } catch (error) {
    // 롤백
    updateLocalAgenda(id, {
      title: oldAgenda.title,
      description: oldAgenda.description
    });
    toast.error('수정에 실패했습니다');
  }
}

// 안건 삭제
async function handleAgendaDelete(id: number) {
  if (!meeting) return;

  const agenda = findAgendaById(id);
  if (!agenda) return;

  // 보호 로직
  if (agenda.time_segments?.length) {
    toast.error('녹음된 구간이 있어 삭제할 수 없습니다');
    return;
  }

  if (id === activeAgendaId) {
    toast.error('현재 녹음 중인 안건은 삭제할 수 없습니다');
    return;
  }

  try {
    await api.delete(`/agendas/${id}`);

    // 로컬 상태에서 제거
    meeting = {
      ...meeting,
      agendas: meeting.agendas.filter(a => a.id !== id)
    };

    // currentAgendaIndex 조정
    if (currentAgendaIndex >= meeting.agendas.length) {
      currentAgendaIndex = Math.max(0, meeting.agendas.length - 1);
    }

    toast.success('안건이 삭제되었습니다');
  } catch (error) {
    toast.error('삭제에 실패했습니다');
  }
}
```

#### 2.3.2 Props 전달

```svelte
<AgendaNotePanel
  agendas={meeting.agendas}
  bind:currentAgendaIndex
  notes={agendaNotes}
  recordingTime={$recordingTime}
  isRecording={$isRecording}
  isPaused={$isPaused}
  activeAgendaId={activeAgendaId}
  onAgendaChange={handleAgendaChange}
  onChildAgendaChange={handleChildAgendaChange}
  onQuestionToggle={handleQuestionToggle}
  onNoteChange={handleNoteChange}
  onAgendaCreate={handleAgendaCreate}
  onAgendaUpdate={handleAgendaUpdate}
  onAgendaDelete={handleAgendaDelete}
/>
```

---

## 3. UI/UX 설계

### 3.1 상태별 UI 표시

| 상태 | 제목 | 삭제 버튼 | 추가 버튼 |
|------|------|----------|----------|
| 녹음 중 + 활성 안건 | 잠금 아이콘 + 배경색 | 숨김 | - |
| 녹음 중 + 비활성 안건 | 편집 가능 | 숨김 | - |
| 녹음 중 (전체) | - | - | 표시 (끝에만) |
| 일시정지/녹음 전 | 편집 가능 | 조건부 표시 | 표시 |

### 3.2 인라인 편집 UX

1. **제목 클릭** → input으로 전환
2. **Enter 또는 blur** → 저장
3. **Escape** → 취소 (원래 값 복원)
4. **빈 값** → 저장 안함, 원래 값 유지

### 3.3 삭제 확인

- 확인 다이얼로그 없음 (빠른 조작 우선)
- toast로 "삭제됨" 피드백
- 향후: Undo 기능 고려

---

## 4. 구현 순서

| 순서 | 작업 | 파일 | 의존성 |
|------|------|------|--------|
| 1 | agenda-permissions.ts 생성 | 신규 | 없음 |
| 2 | AgendaNotePanel Props 확장 | 수정 | 1 |
| 3 | 인라인 편집 UI 구현 | 수정 | 2 |
| 4 | 안건 추가 UI 구현 | 수정 | 2 |
| 5 | 삭제 기능 구현 | 수정 | 2 |
| 6 | record/+page.svelte 핸들러 | 수정 | 2-5 |
| 7 | record/+page.svelte props 연결 | 수정 | 6 |

---

## 5. 테스트 시나리오

### 5.1 권한 테스트

| 시나리오 | 예상 결과 |
|---------|----------|
| 녹음 전 - 제목 편집 | 성공 |
| 녹음 전 - 삭제 | 성공 |
| 녹음 중 - 활성 안건 제목 편집 | 차단 (잠금 아이콘) |
| 녹음 중 - 비활성 안건 제목 편집 | 성공 |
| 녹음 중 - 안건 삭제 | 차단 |
| 녹음 중 - 안건 추가 | 성공 (끝에) |
| 일시정지 - time_segments 있는 안건 삭제 | 차단 |
| 일시정지 - time_segments 없는 안건 삭제 | 성공 |

### 5.2 데이터 무결성 테스트

| 시나리오 | 검증 항목 |
|---------|----------|
| 안건 편집 후 녹음 완료 | time_segments 유지 |
| 안건 추가 후 녹음 | 새 안건에 time_segments 기록 가능 |
| API 실패 시 | 롤백되어 원래 값 유지 |

---

## 6. 파일 체크리스트

- [ ] `frontend/src/lib/utils/agenda-permissions.ts` (신규)
- [ ] `frontend/src/lib/components/recording/AgendaNotePanel.svelte` (수정)
- [ ] `frontend/src/routes/meetings/[id]/record/+page.svelte` (수정)
