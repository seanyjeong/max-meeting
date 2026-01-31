# Design: Meeting UX Overhaul

> 회의 화면 UX 전면 개편 상세 설계

## 1. 현재 구조 분석

### 1.1 레이아웃 구조
```
┌─────────────────────────────────────────────────────────────┐
│ Header (네비게이션)                                          │
├──────────────┬──────────────────────────────────────────────┤
│ Left Panel   │ Right Panel (NoteSketchArea)                 │
│ 25%          │ 75%                                          │
│ (256-320px)  │                                              │
│              │ ┌─────────────────────────────────────────┐  │
│ - 안건 목록   │ │ [텍스트] [스케치]  ← 현재 탭            │  │
│ - 메모 영역   │ ├─────────────────────────────────────────┤  │
│ - 이전/다음   │ │ 에디터 또는 tldraw 캔버스               │  │
│              │ └─────────────────────────────────────────┘  │
└──────────────┴──────────────────────────────────────────────┘
```

### 1.2 현재 문제점
| 항목 | 현재 상태 | 문제 |
|------|----------|------|
| 전체 너비 | max-w-7xl (1280px) | 태블릿(2000px)에서 좁음 |
| 탭 명칭 | 텍스트, 스케치 | 직관적이지 않음 |
| 업무배치 | 없음 (결과에서만) | 회의 중 배정 불가 |
| 스케치 저장 | 메모리만 (휘발) | 새로고침 시 손실 |
| 결과 메모 | 표시 안됨 | 메모 내용 확인 불가 |

## 2. 변경 설계

### 2.1 레이아웃 너비 확대

**변경 대상**: `src/routes/+layout.svelte`

```css
/* Before */
.main-container {
  max-width: 1280px; /* max-w-7xl */
}

/* After */
.main-container {
  max-width: 1900px;
}

/* 반응형 */
@media (max-width: 1600px) {
  .main-container { max-width: 100%; padding: 0 1rem; }
}
```

**회의 페이지**: 이미 전체 viewport 사용 중 (변경 불필요)

### 2.2 탭 구조 변경

**변경 대상**: `src/lib/components/recording/NoteSketchArea.svelte`

```
Before:                    After:
┌─────────┬─────────┐     ┌──────┬──────┬──────────┐
│ 텍스트  │ 스케치  │  →  │ 메모 │ 필기 │ 업무배치 │
└─────────┴─────────┘     └──────┴──────┴──────────┘
```

**코드 변경**:
```svelte
<!-- Before -->
<button class:active={activeTab === 'text'}>텍스트</button>
<button class:active={activeTab === 'sketch'}>스케치</button>

<!-- After -->
<button class:active={activeTab === 'memo'}>메모</button>
<button class:active={activeTab === 'pen'}>필기</button>
<button class:active={activeTab === 'task'}>업무배치</button>
```

### 2.3 업무배치 탭 컴포넌트

**신규 파일**: `src/lib/components/recording/TaskAssignment.svelte`

```svelte
<script lang="ts">
  import { resultsStore, type ActionItem } from '$lib/stores/results';

  interface Props {
    meetingId: number;
  }

  let { meetingId }: Props = $props();

  // 기존 ActionItems 로직 재사용
  let newTask = $state({ content: '', assignee_name: '', due_date: null });
</script>

<div class="task-assignment">
  <div class="header">
    <h3>업무 배치</h3>
    <button onclick={addTask}>+ 업무 추가</button>
  </div>

  <div class="task-list">
    {#each $resultsStore.actionItems as task}
      <div class="task-card">
        <input type="checkbox" checked={task.status === 'completed'} />
        <div class="task-content">
          <p>{task.content}</p>
          <div class="task-meta">
            <span>담당: {task.assignee_name || '-'}</span>
            <span>마감: {task.due_date || '-'}</span>
          </div>
        </div>
        <button class="edit-btn">수정</button>
        <button class="delete-btn">삭제</button>
      </div>
    {/each}
  </div>

  {#if showForm}
    <form onsubmit={handleSubmit}>
      <input placeholder="업무 내용" bind:value={newTask.content} />
      <input placeholder="담당자" bind:value={newTask.assignee_name} />
      <input type="date" bind:value={newTask.due_date} />
      <button type="submit">추가</button>
    </form>
  {/if}
</div>
```

**스타일**:
```css
.task-assignment {
  padding: 1rem;
  height: 100%;
  overflow-y: auto;
}

.task-card {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  margin-bottom: 0.75rem;
}

.task-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  color: #6b7280;
}
```

### 2.4 포스트잇 메모 컴포넌트 (결과 페이지)

**신규 파일**: `src/lib/components/results/PostItNote.svelte`

```svelte
<script lang="ts">
  interface Props {
    content: string;
    agendaTitle?: string;
    color?: 'yellow' | 'pink' | 'green' | 'blue';
  }

  let { content, agendaTitle, color = 'yellow' }: Props = $props();
</script>

<div class="postit postit-{color}">
  {#if agendaTitle}
    <div class="postit-header">{agendaTitle}</div>
  {/if}
  <div class="postit-content">
    {content}
  </div>
</div>

<style>
  .postit {
    position: relative;
    padding: 1rem;
    min-width: 150px;
    max-width: 250px;
    border-radius: 0 0 0.5rem 0.5rem;
    box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    transform: rotate(-1deg);
  }

  .postit::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1.5rem;
    background: linear-gradient(to bottom, rgba(0,0,0,0.05), transparent);
    border-radius: 0.25rem 0.25rem 0 0;
  }

  .postit-yellow { background: #fef9c3; }
  .postit-pink { background: #fce7f3; }
  .postit-green { background: #dcfce7; }
  .postit-blue { background: #dbeafe; }

  .postit-header {
    font-size: 0.7rem;
    color: #6b7280;
    margin-bottom: 0.5rem;
    font-weight: 500;
  }

  .postit-content {
    font-size: 0.875rem;
    line-height: 1.4;
    white-space: pre-wrap;
  }
</style>
```

### 2.5 결과 페이지 메모 섹션

**변경 대상**: `src/routes/meetings/[id]/results/+page.svelte`

```svelte
<!-- 안건 요약 아래에 메모 표시 -->
{#each $resultsStore.agendaSummaries as agenda}
  <div class="agenda-section">
    <h4>{agenda.order_num}. {agenda.title}</h4>
    <p class="summary">{agenda.summary}</p>

    <!-- 메모 포스트잇 -->
    {#if agenda.notes && agenda.notes.length > 0}
      <div class="notes-container">
        {#each agenda.notes as note}
          <PostItNote content={note.content} color="yellow" />
        {/each}
      </div>
    {/if}
  </div>
{/each}
```

## 3. 데이터 흐름

### 3.1 메모 저장 흐름 (현재)
```
AgendaNotePanel (메모 입력)
    ↓
notesStore.saveNote(agendaId, content)
    ↓
IndexedDB (로컬 저장)
```

### 3.2 메모 결과 표시 흐름 (신규)
```
IndexedDB → 회의 완료 시 → Backend API 저장
    ↓
결과 페이지 로드 시 API 조회
    ↓
PostItNote 컴포넌트로 렌더링
```

### 3.3 업무배치 흐름
```
TaskAssignment (회의 중)
    ↓
resultsStore.createActionItem()
    ↓
POST /results/{id}/action-items
    ↓
ActionItems (결과 페이지)에서 동일 데이터 표시
```

## 4. API 변경사항

### 4.1 메모 저장 API (신규 필요)
```
POST /meetings/{meeting_id}/notes
Request:
{
  "agenda_id": 123,
  "content": "메모 내용"
}

GET /meetings/{meeting_id}/notes
Response:
{
  "data": [
    { "id": 1, "agenda_id": 123, "content": "메모1" },
    { "id": 2, "agenda_id": 124, "content": "메모2" }
  ]
}
```

**대안**: 기존 notes 필드가 있다면 활용
- 현재 구조 확인 필요

## 5. 파일 변경 목록

### 5.1 수정 파일
| 파일 | 변경 내용 |
|------|----------|
| `src/routes/+layout.svelte` | max-width 1900px 확대 |
| `src/app.css` | 전역 width 변수 추가 |
| `src/lib/components/recording/NoteSketchArea.svelte` | 탭 명칭 변경 + 업무배치 탭 추가 |
| `src/routes/meetings/[id]/results/+page.svelte` | 메모 포스트잇 표시 섹션 추가 |

### 5.2 신규 파일
| 파일 | 설명 |
|------|------|
| `src/lib/components/recording/TaskAssignment.svelte` | 업무배치 탭 컴포넌트 |
| `src/lib/components/results/PostItNote.svelte` | 포스트잇 메모 컴포넌트 |

### 5.3 백엔드 (필요시)
| 파일 | 설명 |
|------|------|
| `app/routers/notes.py` | 메모 CRUD API (신규) |
| `app/models/note.py` | Note 모델 (신규) |

## 6. 구현 순서

```
Phase 1: 기반 (예상 1시간)
├── 1.1 전역 max-width 확대
├── 1.2 탭 명칭 변경 (텍스트→메모, 스케치→필기)
└── 1.3 빌드 확인

Phase 2: 업무배치 (예상 2시간)
├── 2.1 TaskAssignment.svelte 생성
├── 2.2 NoteSketchArea에 탭 추가
├── 2.3 resultsStore 연동 확인
└── 2.4 테스트

Phase 3: 포스트잇 메모 (예상 2시간)
├── 3.1 메모 데이터 저장 구조 확인/구현
├── 3.2 PostItNote.svelte 생성
├── 3.3 결과 페이지에 메모 섹션 추가
└── 3.4 스타일 조정

Phase 4: 스케치 접근 (브레인스토밍 후)
├── 4.1 스케치 저장 구조 개선
└── 4.2 접근 UI 구현
```

## 7. 테스트 시나리오

### 7.1 화면 크기
- [ ] 태블릿(2000x1200)에서 1900px 폭 확인
- [ ] 모바일 반응형 정상 동작

### 7.2 탭 기능
- [ ] 메모 탭에서 텍스트 입력/저장
- [ ] 필기 탭에서 tldraw 그리기
- [ ] 업무배치 탭에서 업무 추가/수정/삭제

### 7.3 업무배치 연동
- [ ] 회의 중 추가한 업무가 결과 페이지에 표시
- [ ] 결과 페이지에서 수정 시 동기화

### 7.4 메모 표시
- [ ] 안건별 메모가 포스트잇으로 표시
- [ ] 여러 메모 시 적절히 배치

---

**작성일**: 2026-01-31
**참조**: `meeting-ux-overhaul.plan.md`
**상태**: Ready for Implementation
