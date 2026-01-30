# 계층형 안건 시스템 개선 - 상세 설계

> 작성일: 2026-01-30
> Plan 문서: `docs/01-plan/features/hierarchical-agenda-system.plan.md`

## 1. Phase 1: PWA 업데이트 알림 제거

### 변경 파일
- `src/lib/components/UpdateNotifier.svelte`

### 구현
UpdateNotifier 컴포넌트 비활성화 (checkForUpdates 함수 즉시 return)

```svelte
// 방법 1: 컴포넌트 전체 비활성화
async function checkForUpdates() {
  return; // 업데이트 체크 비활성화
}
```

---

## 2. Phase 2: 회의 상세 - 자식안건 토글 표시

### 변경 파일
- `src/routes/meetings/[id]/+page.svelte`

### 현재 구조
```
안건 1
  └─ 토의 질문 (agenda.questions)
안건 2
  └─ 토의 질문
```

### 개선 구조
```
안건 1 [▼ 토글]
  ├─ 자식안건 1-1 [▼]
  │    └─ 토의 질문
  ├─ 자식안건 1-2 [▼]
  │    └─ 토의 질문
  └─ (자식 없으면) 토의 질문
안건 2 [▼ 토글]
  ...
```

### UI 명세
```svelte
{#each $currentMeeting.agendas as agenda, index (agenda.id)}
  <div class="agenda-card">
    <!-- 대안건 헤더 (클릭으로 토글) -->
    <button onclick={() => toggleAgenda(agenda.id)}>
      <span class="chevron">{expandedAgendas.has(agenda.id) ? '▼' : '▶'}</span>
      <span class="order">{index + 1}</span>
      <span class="title">{agenda.title}</span>
    </button>

    {#if expandedAgendas.has(agenda.id)}
      <!-- 자식안건이 있으면 -->
      {#if agenda.children?.length > 0}
        {#each agenda.children as child, childIndex}
          <div class="child-agenda indent-1">
            <button onclick={() => toggleChild(child.id)}>
              <span>{index + 1}.{childIndex + 1}</span>
              <span>{child.title}</span>
            </button>
            {#if expandedChildren.has(child.id)}
              <!-- 자식안건의 질문 -->
              {#each child.questions as q}
                <div class="question">{q.question}</div>
              {/each}
            {/if}
          </div>
        {/each}
      {:else}
        <!-- 자식안건 없으면 대안건의 질문 표시 -->
        {#each agenda.questions as q}
          <div class="question">{q.question}</div>
        {/each}
      {/if}
    {/if}
  </div>
{/each}
```

### 상태 관리
```typescript
let expandedAgendas = $state(new Set<number>());
let expandedChildren = $state(new Set<number>());

function toggleAgenda(id: number) {
  if (expandedAgendas.has(id)) {
    expandedAgendas.delete(id);
  } else {
    expandedAgendas.add(id);
  }
  expandedAgendas = new Set(expandedAgendas); // 반응성 트리거
}
```

---

## 3. Phase 3: 녹음 페이지 - 자식안건 타임스탬프

### 변경 파일
- `src/lib/components/recording/AgendaNotePanel.svelte`
- `src/routes/meetings/[id]/record/+page.svelte`

### 현재 동작
- 대안건만 목록에 표시
- 자식안건은 "하위 토픽"으로 텍스트만 표시 (클릭 불가)

### 개선 동작
- 대안건 선택 시 자식안건들도 클릭 가능하게 표시
- 자식안건 클릭 → 해당 자식안건에 time_segments 저장
- 다음/이전 버튼은 대안건만 이동 (현재 로직 유지)

### 안건 목록 UI 개선
```svelte
<!-- 안건 목록에 자식안건 포함 -->
{#each agendas as agenda, index (agenda.id)}
  <!-- 대안건 -->
  <button onclick={() => goToAgenda(index)}>
    {agenda.order_num}. {agenda.title}
  </button>

  <!-- 자식안건들 (indent) -->
  {#if agenda.children?.length > 0}
    {#each agenda.children as child, childIdx}
      <button
        class="ml-4 text-sm"
        onclick={() => goToChildAgenda(agenda.id, child.id)}
      >
        {agenda.order_num}.{childIdx + 1} {child.title}
      </button>
    {/each}
  {/if}
{/each}
```

### 자식안건 타임스탬프 처리
```typescript
// 현재 활성 항목 (대안건 또는 자식안건)
let activeItemId = $state<number | null>(null);
let activeItemType = $state<'agenda' | 'child'>('agenda');

async function goToChildAgenda(parentId: number, childId: number) {
  // 이전 항목 segment 닫기
  if (activeItemId !== null) {
    await closeSegment(activeItemId, recordingTime);
  }

  // 자식안건 segment 열기
  await openSegment(childId, recordingTime);
  activeItemId = childId;
  activeItemType = 'child';

  // 부모 안건 인덱스로 이동 (UI 표시용)
  currentAgendaIndex = agendas.findIndex(a => a.id === parentId);
}
```

### time_segments 저장 대상
- 대안건: `agenda.time_segments`
- 자식안건: `child.time_segments` (DB에 이미 지원됨 - agendas 테이블 공유)

---

## 4. Phase 4: 결과 페이지 - 계층형 대화 내용

### 변경 파일
- `src/lib/components/results/TranscriptViewer.svelte`

### 현재 구조
```
[전체] [안건1] [안건2] [안건3]  ← 플랫 탭
```

### 개선 구조
```
[전체] [안건1 ▼] [안건2 ▼]  ← 드롭다운 메뉴
         ├─ 전체
         ├─ 자식안건 1-1
         └─ 자식안건 1-2
```

### UI 명세
```svelte
<div class="agenda-filter">
  <!-- 전체 버튼 -->
  <button class:active={selectedAgendaId === 'all'}>전체</button>

  <!-- 대안건별 드롭다운 -->
  {#each agendas as agenda}
    <div class="dropdown">
      <button class:active={selectedAgendaId === agenda.id}>
        {agenda.order_num}. {truncate(agenda.title, 10)}
        {#if agenda.children?.length > 0}
          <span class="chevron">▼</span>
        {/if}
      </button>

      {#if agenda.children?.length > 0}
        <div class="dropdown-menu">
          <button onclick={() => selectAgenda(agenda.id, 'all')}>
            전체
          </button>
          {#each agenda.children as child}
            <button onclick={() => selectAgenda(agenda.id, child.id)}>
              {child.title}
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/each}
</div>
```

### 필터링 로직
```typescript
let selectedAgendaId = $state<number | 'all'>('all');
let selectedChildId = $state<number | 'all'>('all');

function isSegmentInSelection(segment: TranscriptSegment): boolean {
  if (selectedAgendaId === 'all') return true;

  const agenda = agendas.find(a => a.id === selectedAgendaId);
  if (!agenda) return false;

  // 자식안건 필터
  if (selectedChildId !== 'all') {
    const child = agenda.children?.find(c => c.id === selectedChildId);
    if (child) return isSegmentInAgenda(segment, child);
    return false;
  }

  // 대안건 전체 (자식안건 포함)
  if (isSegmentInAgenda(segment, agenda)) return true;
  for (const child of agenda.children || []) {
    if (isSegmentInAgenda(segment, child)) return true;
  }
  return false;
}
```

---

## 5. Phase 5: 질문 생성 - 자식안건 우선 로직

### 변경 파일
- `backend/app/services/llm.py`
- `backend/workers/tasks/llm.py`

### 현재 로직
- 대안건에만 질문 생성

### 개선 로직
```python
async def generate_questions_for_meeting(meeting_id: int):
    """회의의 모든 안건에 질문 생성"""
    agendas = await get_agendas(meeting_id)

    for agenda in agendas:
        # 자식안건이 있으면 자식안건에 질문 생성
        if agenda.children:
            for child in agenda.children:
                await generate_questions(child.id)
        else:
            # 자식안건 없으면 대안건에 질문 생성
            await generate_questions(agenda.id)
```

---

## 6. Phase 6: PDF 회의록 페이지

### 신규 파일
- `src/routes/meetings/[id]/results/report/+page.svelte`
- `src/lib/components/results/MeetingReport.svelte`

### 라우트 구조
```
/meetings/[id]/results         ← 기존 결과 페이지
/meetings/[id]/results/report  ← 신규 PDF 회의록 페이지
```

### MeetingReport 컴포넌트 구조
```svelte
<div class="meeting-report print:bg-white">
  <!-- 헤더 -->
  <header class="report-header">
    <h1>{meeting.title}</h1>
    <div class="meta">
      <span>일시: {formatDate(meeting.scheduled_at)}</span>
      <span>장소: {meeting.location}</span>
    </div>
    <div class="attendees">
      참석자: {meeting.attendees.map(a => a.contact?.name).join(', ')}
    </div>
  </header>

  <!-- 요약 -->
  <section class="summary">
    <h2>회의 요약</h2>
    <p>{result.summary}</p>
  </section>

  <!-- 안건별 상세 -->
  {#each agendas as agenda, idx}
    <section class="agenda-section">
      <h2>{idx + 1}. {agenda.title}</h2>

      <!-- 자식안건들 -->
      {#each agenda.children || [] as child, childIdx}
        <div class="child-section">
          <h3>{idx + 1}.{childIdx + 1} {child.title}</h3>

          <!-- 토론 내용 -->
          <div class="discussion">
            <h4>토론 내용</h4>
            <p>{getDiscussion(child.id)}</p>
          </div>

          <!-- 메모 -->
          {#if getNotes(child.id)}
            <div class="notes">
              <h4>메모</h4>
              <p>{getNotes(child.id)}</p>
            </div>
          {/if}
        </div>
      {/each}

      <!-- 자식안건 없으면 대안건 내용 -->
      {#if !agenda.children?.length}
        <div class="discussion">
          <p>{getDiscussion(agenda.id)}</p>
        </div>
        {#if getNotes(agenda.id)}
          <div class="notes">
            <h4>메모</h4>
            <p>{getNotes(agenda.id)}</p>
          </div>
        {/if}
      {/if}
    </section>
  {/each}

  <!-- 실행 항목 -->
  <section class="action-items">
    <h2>실행 항목</h2>
    {#each actionItems as item}
      <div class="action-item">
        <span class="checkbox">☐</span>
        <span>{item.content}</span>
        {#if item.assignee_name}
          <span class="assignee">- {item.assignee_name}</span>
        {/if}
      </div>
    {/each}
  </section>

  <!-- 필기 보기 버튼 -->
  <section class="sketches">
    <h2>필기 내용</h2>
    <button onclick={() => showSketches = true}>
      필기 내용 보기 ({sketches.length}개)
    </button>
  </section>
</div>

<!-- 필기 모달 -->
{#if showSketches}
  <SketchModal agendas={agendas} sketches={sketches} />
{/if}
```

### 프린트 스타일
```css
@media print {
  .meeting-report {
    font-size: 11pt;
    line-height: 1.5;
  }

  .report-header {
    border-bottom: 2px solid #000;
    margin-bottom: 1rem;
  }

  .agenda-section {
    page-break-inside: avoid;
  }

  .no-print {
    display: none;
  }
}
```

---

## 7. 구현 순서

```
1. Phase 1: UpdateNotifier 비활성화 (5분)
2. Phase 2: 회의 상세 토글 UI (30분)
3. Phase 3: 녹음 페이지 자식안건 클릭 (45분)
4. Phase 4: 결과 페이지 계층 필터 (30분)
5. Phase 5: 질문 생성 로직 수정 (20분)
6. Phase 6: PDF 회의록 페이지 (60분)
```

---

## 8. 검증 체크리스트

### Phase 1 ✅ 완료
- [x] PWA 업데이트 알림 미노출

### Phase 2 ✅ 완료
- [x] 대안건 토글 열기/닫기
- [x] 자식안건 표시
- [x] 자식안건 질문 표시

### Phase 3 ✅ 완료
- [x] 자식안건 클릭 → 타임스탬프 저장
- [x] 안건 목록에 자식안건 표시
- [x] 다음/이전 버튼은 대안건만

### Phase 4 ✅ 완료
- [x] 대안건 탭 클릭 → 필터링
- [x] 자식안건 서브메뉴 → 세부 필터링

### Phase 5 ✅ 완료
- [x] 자식안건에 질문 생성 확인
- [x] 자식안건 없으면 대안건에 질문

### Phase 6 ✅ 완료
- [x] 회의록 페이지 렌더링
- [x] 안건별 내용 정리
- [x] 메모 표시
- [x] 필기 모달

---

## 9. 구현 결과

### 변경된 파일

1. **`src/lib/components/UpdateNotifier.svelte`** - PWA 업데이트 알림 비활성화
2. **`src/routes/meetings/[id]/+page.svelte`** - 자식안건 토글 UI
3. **`src/lib/components/recording/AgendaNotePanel.svelte`** - 자식안건 클릭/타임스탬프
4. **`src/routes/meetings/[id]/record/+page.svelte`** - 자식안건 핸들러
5. **`src/lib/components/results/TranscriptViewer.svelte`** - 계층형 필터 드롭다운
6. **`backend/app/routers/agendas.py`** - 질문 생성 로직 (자식안건 우선)
7. **`src/routes/meetings/[id]/results/report/+page.svelte`** (신규) - PDF 회의록 페이지
8. **`src/routes/meetings/[id]/results/+page.svelte`** - 회의록 페이지 링크 추가

### 다음 단계

`/pdca analyze hierarchical-agenda-system` 으로 Gap 분석 진행
