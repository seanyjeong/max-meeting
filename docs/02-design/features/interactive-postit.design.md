# Design: 인터랙티브 포스트잇

## 1. 개요

| 항목 | 내용 |
|------|------|
| Feature | interactive-postit |
| Plan 참조 | [interactive-postit.plan.md](../../01-plan/features/interactive-postit.plan.md) |
| 작성일 | 2026-01-31 |
| 상태 | Design 진행 중 |

---

## 2. 데이터 모델

### 2.1 DB 스키마 변경

```sql
-- 기존 manual_notes 테이블에 컬럼 추가
ALTER TABLE manual_notes ADD COLUMN position_x FLOAT DEFAULT NULL;
ALTER TABLE manual_notes ADD COLUMN position_y FLOAT DEFAULT NULL;
ALTER TABLE manual_notes ADD COLUMN rotation FLOAT DEFAULT NULL;
ALTER TABLE manual_notes ADD COLUMN is_visible BOOLEAN DEFAULT TRUE;
ALTER TABLE manual_notes ADD COLUMN z_index INTEGER DEFAULT 0;
```

### 2.2 SQLAlchemy 모델

**파일**: `backend/app/models/note.py`

```python
class ManualNote(Base):
    __tablename__ = "manual_notes"

    # 기존 필드
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"))
    agenda_id: Mapped[int | None] = mapped_column(ForeignKey("agendas.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    # 새 필드 (인터랙티브 포스트잇)
    position_x: Mapped[float | None] = mapped_column(Float, default=None)
    position_y: Mapped[float | None] = mapped_column(Float, default=None)
    rotation: Mapped[float | None] = mapped_column(Float, default=None)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    z_index: Mapped[int] = mapped_column(Integer, default=0)
```

### 2.3 Pydantic 스키마

**파일**: `backend/app/schemas/note.py`

```python
class NotePositionUpdate(BaseModel):
    """포스트잇 위치 업데이트"""
    position_x: float = Field(..., ge=0, le=100, description="X 좌표 (%)")
    position_y: float = Field(..., ge=0, le=100, description="Y 좌표 (%)")
    z_index: int | None = Field(None, description="레이어 순서")

class NoteVisibilityUpdate(BaseModel):
    """포스트잇 표시/숨김"""
    is_visible: bool

class NoteResponse(BaseModel):
    """메모 응답 (확장)"""
    id: int
    meeting_id: int
    agenda_id: int | None
    content: str
    position_x: float | None
    position_y: float | None
    rotation: float | None
    is_visible: bool
    z_index: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## 3. API 설계

### 3.1 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `PATCH` | `/notes/{id}/position` | 위치 업데이트 |
| `PATCH` | `/notes/{id}/visibility` | 표시/숨김 토글 |
| `DELETE` | `/notes/{id}` | 메모 삭제 (기존) |

### 3.2 API 상세

**파일**: `backend/app/routers/notes.py`

```python
@router.patch("/{note_id}/position")
async def update_note_position(
    note_id: int,
    position: NotePositionUpdate,
    db: AsyncSession = Depends(get_db)
) -> NoteResponse:
    """포스트잇 위치 업데이트"""
    note = await db.get(ManualNote, note_id)
    if not note:
        raise HTTPException(404, "Note not found")

    note.position_x = position.position_x
    note.position_y = position.position_y
    if position.z_index is not None:
        note.z_index = position.z_index

    await db.commit()
    await db.refresh(note)
    return note

@router.patch("/{note_id}/visibility")
async def update_note_visibility(
    note_id: int,
    visibility: NoteVisibilityUpdate,
    db: AsyncSession = Depends(get_db)
) -> NoteResponse:
    """포스트잇 표시/숨김 토글"""
    note = await db.get(ManualNote, note_id)
    if not note:
        raise HTTPException(404, "Note not found")

    note.is_visible = visibility.is_visible
    await db.commit()
    await db.refresh(note)
    return note
```

---

## 4. 프론트엔드 설계

### 4.1 컴포넌트 구조

```
frontend/src/lib/components/
├── results/
│   ├── PostItNote.svelte          # 기존 (스타일만)
│   ├── DraggablePostIt.svelte     # 새로 생성 (드래그 기능)
│   └── PostItCanvas.svelte        # 새로 생성 (컨테이너)
```

### 4.2 DraggablePostIt.svelte

```svelte
<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import PostItNote from './PostItNote.svelte';

    interface Props {
        note: {
            id: number;
            content: string;
            position_x: number | null;
            position_y: number | null;
            rotation: number | null;
            z_index: number;
        };
        color?: 'yellow' | 'pink' | 'green' | 'blue';
        editable?: boolean;
    }

    let { note, color = 'yellow', editable = true }: Props = $props();

    const dispatch = createEventDispatcher<{
        move: { id: number; x: number; y: number };
        delete: { id: number };
    }>();

    let isDragging = $state(false);
    let showActions = $state(false);
    let startX = 0;
    let startY = 0;
    let currentX = $state(note.position_x ?? 10);
    let currentY = $state(note.position_y ?? 10);

    function handleMouseDown(e: MouseEvent) {
        if (!editable) return;
        isDragging = true;
        startX = e.clientX - currentX;
        startY = e.clientY - currentY;
    }

    function handleMouseMove(e: MouseEvent) {
        if (!isDragging) return;
        currentX = Math.max(0, Math.min(100, e.clientX - startX));
        currentY = Math.max(0, Math.min(100, e.clientY - startY));
    }

    function handleMouseUp() {
        if (isDragging) {
            isDragging = false;
            dispatch('move', { id: note.id, x: currentX, y: currentY });
        }
    }

    function handleDelete() {
        dispatch('delete', { id: note.id });
    }

    // 회전 각도 (랜덤 또는 저장된 값)
    let rotation = $derived(note.rotation ?? (Math.random() * 6 - 3));
</script>

<svelte:window
    on:mousemove={handleMouseMove}
    on:mouseup={handleMouseUp}
    on:touchmove={handleTouchMove}
    on:touchend={handleMouseUp}
/>

<div
    class="draggable-postit"
    class:dragging={isDragging}
    style="
        left: {currentX}%;
        top: {currentY}%;
        transform: rotate({rotation}deg);
        z-index: {note.z_index};
    "
    on:mousedown={handleMouseDown}
    on:touchstart={handleTouchStart}
    on:mouseenter={() => showActions = true}
    on:mouseleave={() => showActions = false}
    role="button"
    tabindex="0"
>
    {#if editable && showActions}
        <button class="delete-btn" on:click|stopPropagation={handleDelete}>
            ✕
        </button>
    {/if}

    <PostItNote content={note.content} {color} small />
</div>

<style>
    .draggable-postit {
        position: absolute;
        cursor: grab;
        transition: transform 0.1s ease, box-shadow 0.2s ease;
    }

    .draggable-postit:hover {
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        z-index: 1000 !important;
    }

    .draggable-postit.dragging {
        cursor: grabbing;
        box-shadow: 0 12px 28px rgba(0,0,0,0.2);
        z-index: 9999 !important;
    }

    .delete-btn {
        position: absolute;
        top: -8px;
        right: -8px;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #ef4444;
        color: white;
        border: 2px solid white;
        font-size: 12px;
        cursor: pointer;
        z-index: 10;
    }

    .delete-btn:hover {
        background: #dc2626;
    }
</style>
```

### 4.3 PostItCanvas.svelte

```svelte
<script lang="ts">
    import DraggablePostIt from './DraggablePostIt.svelte';
    import { api } from '$lib/api';

    interface Note {
        id: number;
        agenda_id: number | null;
        content: string;
        position_x: number | null;
        position_y: number | null;
        rotation: number | null;
        is_visible: boolean;
        z_index: number;
    }

    interface Props {
        notes: Note[];
        agendaId?: number;
        editable?: boolean;
    }

    let { notes, agendaId, editable = true }: Props = $props();

    // 필터: 해당 안건의 visible 메모만
    let visibleNotes = $derived(
        notes.filter(n =>
            n.is_visible &&
            (agendaId ? n.agenda_id === agendaId : true)
        )
    );

    const colors: Array<'yellow' | 'pink' | 'green' | 'blue'> =
        ['yellow', 'pink', 'green', 'blue'];

    async function handleMove(e: CustomEvent<{ id: number; x: number; y: number }>) {
        const { id, x, y } = e.detail;
        try {
            await api.patch(`/notes/${id}/position`, {
                position_x: x,
                position_y: y
            });
        } catch (error) {
            console.error('Failed to update position:', error);
        }
    }

    async function handleDelete(e: CustomEvent<{ id: number }>) {
        const { id } = e.detail;
        try {
            await api.patch(`/notes/${id}/visibility`, {
                is_visible: false
            });
            // UI에서 제거 (reactivity)
            notes = notes.map(n =>
                n.id === id ? { ...n, is_visible: false } : n
            );
        } catch (error) {
            console.error('Failed to hide note:', error);
        }
    }
</script>

<div class="postit-canvas">
    {#each visibleNotes as note, idx (note.id)}
        <DraggablePostIt
            {note}
            color={colors[idx % colors.length]}
            {editable}
            on:move={handleMove}
            on:delete={handleDelete}
        />
    {/each}
</div>

<style>
    .postit-canvas {
        position: relative;
        width: 100%;
        min-height: 300px;
        background: #f9fafb;
        border: 2px dashed #e5e7eb;
        border-radius: 0.75rem;
        overflow: hidden;
    }
</style>
```

---

## 5. 페이지 통합

### 5.1 결과 페이지 (편집 모드)

**파일**: `frontend/src/routes/meetings/[id]/results/+page.svelte`

```svelte
<!-- 메모 탭 내용 -->
{#if activeTab === 'memos'}
    <PostItCanvas
        notes={allNotes}
        editable={true}
    />
{/if}
```

### 5.2 회의록 페이지 (읽기 전용)

**파일**: `frontend/src/routes/meetings/[id]/results/report/+page.svelte`

```svelte
<!-- 기존 고정 레이아웃 유지 (인쇄용) -->
<div class="notes-section">
    {#each visibleNotes as note}
        <PostItNote content={note.content} color="yellow" small />
    {/each}
</div>
```

---

## 6. 구현 순서

### Phase 1: 기본 드래그 (MVP)

| 순서 | 작업 | 파일 |
|------|------|------|
| 1 | DB 마이그레이션 | `migrations/` |
| 2 | 모델 필드 추가 | `models/note.py` |
| 3 | 스키마 추가 | `schemas/note.py` |
| 4 | API 추가 | `routers/notes.py` |
| 5 | DraggablePostIt 컴포넌트 | `components/results/` |
| 6 | PostItCanvas 컴포넌트 | `components/results/` |
| 7 | 결과 페이지 통합 | `results/+page.svelte` |

### Phase 2: 삭제 & 시각 효과

| 순서 | 작업 |
|------|------|
| 1 | 삭제 버튼 UI |
| 2 | 숨김 API 연동 |
| 3 | 회전 효과 |
| 4 | 그림자/호버 효과 |
| 5 | 터치 이벤트 지원 |

---

## 7. 테스트 계획

- [ ] DB 마이그레이션 성공
- [ ] 위치 업데이트 API 작동
- [ ] 드래그 후 위치 저장됨
- [ ] 새로고침 후 위치 유지
- [ ] 삭제 버튼으로 숨김 처리
- [ ] 모바일 터치 드래그 작동
- [ ] 회의록 페이지에서 고정 레이아웃 유지

---

## 8. 참고사항

- **디바운스**: 위치 업데이트 API는 드래그 종료 시에만 호출
- **z-index**: 클릭한 메모를 최상위로 올림
- **인쇄**: 회의록 페이지에서는 position 무시, 순차 배치
- **호환성**: 기존 메모(position=null)는 기본 위치에 표시
