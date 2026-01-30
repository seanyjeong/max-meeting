# Design: 안건별 다중 시간 구간 (time-segments)

> 생성일: 2026-01-30
> Plan 참조: [time-segments.plan.md](../../01-plan/features/time-segments.plan.md)

---

## 1. UI 설계 (11인치 태블릿 기준)

### 1.1 디바이스 스펙

| 디바이스 | 해상도 | CSS 픽셀 |
|----------|--------|----------|
| iPad Pro 11" | 2388×1668 | ~1194×834 |
| Galaxy Tab S8 11" | 2560×1600 | ~1280×800 |
| **설계 기준** | - | **1200×800** |

### 1.2 전체 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CompactRecordingBar (56px)                                          [마무리]│
├─────────────────────────────────────────────────────────────────────────────┤
│ Breadcrumb (52px)                                                           │
├──────────────────────┬──────────────────────────────────────────────────────┤
│                      │                                                      │
│   AgendaNotePanel    │              NoteSketchArea                         │
│   (300px 고정)       │              (나머지)                                │
│                      │                                                      │
│   ┌──────────────┐   │                                                      │
│   │ 안건 목록    │   │                                                      │
│   │ (최대 180px) │   │                                                      │
│   ├──────────────┤   │                                                      │
│   │              │   │                                                      │
│   │ 현재 안건    │   │                                                      │
│   │ 상세 영역    │   │                                                      │
│   │ (스크롤)     │   │                                                      │
│   │              │   │                                                      │
│   ├──────────────┤   │                                                      │
│   │ [이전][다음] │   │                                                      │
│   └──────────────┘   │                                                      │
│                      │                                                      │
└──────────────────────┴──────────────────────────────────────────────────────┘
```

### 1.3 AgendaNotePanel 상세 설계

**왼쪽 패널 (300px 고정)**

```
┌────────────────────────────────────┐
│ 📋 안건 목록                    ▼  │  ← 접기/펼치기 토글
├────────────────────────────────────┤
│ ┌────────────────────────────────┐ │
│ │ ✓ 1. 인사말           00:00   │ │  ← 완료 (회색)
│ ├────────────────────────────────┤ │
│ │ ▶ 2. 예산 검토        00:30   │ │  ← 현재 (파란색 하이라이트)
│ ├────────────────────────────────┤ │
│ │   3. 일정 조율        —       │ │  ← 대기 (기본)
│ ├────────────────────────────────┤ │
│ │   4. 기타 논의        —       │ │
│ └────────────────────────────────┘ │
│         최대 180px, 초과 시 스크롤   │
├────────────────────────────────────┤
│                                    │
│ ┌────────────────────────────────┐ │
│ │ 2. 예산 검토                   │ │  ← 현재 안건 제목
│ │ ┌─────────────────────────────┐│ │
│ │ │ 진행중  ⏱ 00:30~           ││ │  ← 상태 + 시간
│ │ └─────────────────────────────┘│ │
│ └────────────────────────────────┘ │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ 📝 상세 내용                   │ │
│ │ 분기별 예산 검토 및 조정...    │ │
│ └────────────────────────────────┘ │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ 📌 하위 토픽                   │ │
│ │ • 1분기 실적                   │ │
│ │ • 2분기 계획                   │ │
│ └────────────────────────────────┘ │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ ☑ 질문 체크리스트    (2/3)    │ │
│ │ ☑ 예산 초과 항목?              │ │
│ │ ☑ 조정 필요 부분?              │ │
│ │ ☐ 다음 분기 예측?              │ │
│ └────────────────────────────────┘ │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ 💬 메모                        │ │
│ │ ┌─────────────────────────────┐│ │
│ │ │                             ││ │
│ │ │ (textarea)                  ││ │
│ │ │                             ││ │
│ │ └─────────────────────────────┘│ │
│ └────────────────────────────────┘ │
│                                    │
├────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐  │
│ │   ◀ 이전    │ │    다음 ▶   │  │  ← 52px 높이, 터치 최적화
│ └──────────────┘ └──────────────┘  │
└────────────────────────────────────┘
```

### 1.4 안건 목록 항목 상세

```
┌─────────────────────────────────────────┐
│ [상태] [번호]. [제목...]     [시간]     │
│  24px    고정    flex-1       56px      │
└─────────────────────────────────────────┘

높이: 48px (터치 타겟 최소 44px 준수)
패딩: 12px 16px
```

**상태 아이콘:**
- `✓` 완료 (초록색) - 해당 안건 논의 완료
- `▶` 현재 (파란색) - 현재 진행 중
- `○` 대기 (회색) - 아직 시작 안함
- `↺` 재방문 (보라색) - 이전에 논의했고 다시 돌아옴

**시간 표시:**
- 시작 시간 있으면: `00:30`
- 여러 구간이면: `00:30 +1` (재방문 횟수)
- 없으면: `—`

### 1.5 터치 타겟 & 간격 규칙

| 요소 | 최소 크기 | 실제 적용 |
|------|-----------|-----------|
| 안건 항목 | 44×44px | 48px 높이, 전체 너비 |
| 이전/다음 버튼 | 44×44px | 52px 높이, 50% 너비 |
| 체크박스 | 44×44px | 48px 터치 영역 |
| 목록 접기 버튼 | 44×44px | 44px |

**간격:**
- 섹션 간: 16px
- 항목 간: 8px
- 내부 패딩: 12-16px

### 1.6 반응형 고려사항

```css
/* 태블릿 세로 모드 (800px 이하) */
@media (max-width: 800px) {
  .agenda-panel {
    /* 하단 드로어로 전환 또는 오버레이 */
  }
}

/* 현재 설계는 가로 모드 기준 */
```

---

## 2. 데이터베이스 설계

### 2.1 스키마 변경

```sql
-- Migration: add_time_segments_to_agendas
ALTER TABLE agendas ADD COLUMN time_segments JSONB DEFAULT NULL;

-- Index for JSON queries (optional, for performance)
CREATE INDEX idx_agendas_time_segments ON agendas USING GIN (time_segments);
```

### 2.2 time_segments 구조

```typescript
interface TimeSegment {
  start: number;  // 시작 시간 (초)
  end: number | null;  // 종료 시간 (초), null = 진행 중
}

// 예시
[
  { "start": 0, "end": 30 },      // 첫 번째 구간
  { "start": 60, "end": 80 }      // 재방문 구간
]
```

### 2.3 하위 호환성

| 조건 | 동작 |
|------|------|
| `time_segments` = null | 기존 `started_at_seconds` 사용 |
| `time_segments` = [] | 타임스탬프 없음 |
| `time_segments` 존재 | 여러 구간 합산 |

**동기화**: `started_at_seconds` = `time_segments[0].start`

---

## 3. Backend API 설계

### 3.1 모델 (agenda.py)

```python
from sqlalchemy import JSON

class Agenda(Base):
    # 기존 필드...
    started_at_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 새 필드
    time_segments: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
```

### 3.2 스키마 (schemas/agenda.py)

```python
class TimeSegment(BaseModel):
    start: int = Field(..., ge=0)
    end: int | None = Field(None, ge=0)

class AgendaUpdate(BaseModel):
    # 기존...
    time_segments: list[TimeSegment] | None = None

class AgendaResponse(AgendaBase):
    # 기존...
    time_segments: list[TimeSegment] | None = None
```

### 3.3 API (기존 PATCH 사용)

```
PATCH /agendas/{agenda_id}
Body: {
  "time_segments": [
    {"start": 0, "end": 30},
    {"start": 60, "end": null}
  ]
}
```

---

## 4. Frontend 설계

### 4.1 타입 (stores/meeting.ts)

```typescript
export interface TimeSegment {
  start: number;
  end: number | null;
}

export interface Agenda {
  // 기존...
  started_at_seconds: number | null;
  time_segments: TimeSegment[] | null;
}
```

### 4.2 녹음 페이지 상태

```typescript
// record/+page.svelte
let activeAgendaId = $state<number | null>(null);
let segmentStartTime = $state<number | null>(null);
```

### 4.3 안건 전환 핵심 로직

```typescript
async function handleAgendaChange(newAgendaId: number, currentTime: number) {
  // 1. 이전 안건 구간 닫기
  if (activeAgendaId && activeAgendaId !== newAgendaId) {
    await closeSegment(activeAgendaId, currentTime);
  }

  // 2. 새 안건 구간 시작
  await openSegment(newAgendaId, currentTime);

  // 3. 상태 업데이트
  activeAgendaId = newAgendaId;
  segmentStartTime = currentTime;
}

async function closeSegment(agendaId: number, endTime: number) {
  const agenda = meeting.agendas.find(a => a.id === agendaId);
  if (!agenda) return;

  const segments = [...(agenda.time_segments || [])];
  const lastSeg = segments[segments.length - 1];

  if (lastSeg && lastSeg.end === null) {
    lastSeg.end = endTime;
    await api.patch(`/agendas/${agendaId}`, { time_segments: segments });
    updateLocalAgenda(agendaId, { time_segments: segments });
  }
}

async function openSegment(agendaId: number, startTime: number) {
  const agenda = meeting.agendas.find(a => a.id === agendaId);
  if (!agenda) return;

  const segments = [...(agenda.time_segments || [])];
  segments.push({ start: startTime, end: null });

  await api.patch(`/agendas/${agendaId}`, { time_segments: segments });
  updateLocalAgenda(agendaId, {
    time_segments: segments,
    started_at_seconds: segments[0].start
  });
}
```

### 4.4 AgendaNotePanel 컴포넌트 변경

```svelte
<!-- 새로운 Props -->
interface Props {
  agendas: Agenda[];
  currentAgendaIndex: number;
  notes: Map<number, string>;
  recordingTime: number;
  isRecording: boolean;  // 새로 추가
  onAgendaChange: (agendaId: number, currentTime: number) => void;  // 변경
  onQuestionToggle: (questionId: number, answered: boolean) => void;
  onNoteChange: (agendaId: number, content: string) => void;
}

<!-- 안건 목록 섹션 -->
<div class="agenda-list-section">
  <button class="list-header" onclick={toggleListCollapse}>
    <span>📋 안건 목록</span>
    <ChevronIcon collapsed={listCollapsed} />
  </button>

  {#if !listCollapsed}
    <div class="agenda-list" style="max-height: 180px; overflow-y: auto;">
      {#each agendas as agenda, index (agenda.id)}
        <button
          class="agenda-item"
          class:current={index === currentAgendaIndex}
          class:completed={agenda.status === 'completed'}
          class:revisited={hasMultipleSegments(agenda)}
          onclick={() => handleAgendaClick(index)}
        >
          <span class="status-icon">{getStatusIcon(agenda, index)}</span>
          <span class="title">{agenda.order_num}. {truncate(agenda.title, 16)}</span>
          <span class="time">{formatAgendaTime(agenda)}</span>
        </button>
      {/each}
    </div>
  {/if}
</div>
```

### 4.5 헬퍼 함수들

```typescript
function getStatusIcon(agenda: Agenda, index: number): string {
  if (index === currentAgendaIndex) return '▶';
  if (agenda.status === 'completed') return '✓';
  if (hasMultipleSegments(agenda)) return '↺';
  if (agenda.time_segments?.length) return '○';
  return '○';
}

function hasMultipleSegments(agenda: Agenda): boolean {
  return (agenda.time_segments?.length ?? 0) > 1;
}

function formatAgendaTime(agenda: Agenda): string {
  if (!agenda.time_segments?.length) return '—';
  const first = agenda.time_segments[0];
  const time = formatTime(first.start);
  if (agenda.time_segments.length > 1) {
    return `${time} +${agenda.time_segments.length - 1}`;
  }
  return time;
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + '…';
}
```

---

## 5. LLM 처리 설계

### 5.1 Transcript 추출 로직

```python
# workers/tasks/llm.py

def get_agenda_transcript(agenda, all_segments: list[dict]) -> str:
    """안건의 모든 시간 구간에서 transcript 추출"""

    if agenda.time_segments:
        # 여러 구간 합산
        texts = []
        for seg in agenda.time_segments:
            start = seg['start']
            end = seg.get('end') or float('inf')

            matching = [
                s['text'] for s in all_segments
                if start <= s['start'] < end and s['text']
            ]
            texts.extend(matching)
        return ' '.join(texts)

    elif agenda.started_at_seconds is not None:
        # 기존 로직 (하위 호환)
        # 다음 안건 시작까지로 처리
        ...

    return ''
```

### 5.2 처리 흐름

```
1. 모든 transcript segments 시간순 정렬
2. 각 안건별:
   if time_segments 존재:
     → 여러 구간 합산
   elif started_at_seconds 존재:
     → 기존 로직 (다음 안건까지)
   else:
     → 빈 문자열
3. LLM에 안건별 transcript 전달
```

---

## 6. 결과 페이지 - 안건별 대화 탭

### 6.1 TranscriptViewer 변경

```svelte
<script lang="ts">
  interface Props {
    agendas?: Agenda[];
    showAgendaTabs?: boolean;
  }

  let selectedAgendaId = $state<number | 'all'>('all');

  // 안건별 필터링
  let filteredSegments = $derived(() => {
    let segments = $resultsStore.transcriptSegments;

    // 기존 필터 (검색, 화자)...

    // 안건 필터
    if (selectedAgendaId !== 'all' && agendas) {
      const agenda = agendas.find(a => a.id === selectedAgendaId);
      if (agenda?.time_segments) {
        segments = segments.filter(seg =>
          agenda.time_segments!.some(
            ts => seg.start >= ts.start && seg.start < (ts.end ?? Infinity)
          )
        );
      }
    }

    return segments;
  });
</script>

<!-- 안건 탭 (가로 스크롤) -->
{#if showAgendaTabs && agendas?.length}
  <div class="flex gap-2 mb-4 overflow-x-auto pb-2 scrollbar-hide">
    <button
      class="tab-btn"
      class:active={selectedAgendaId === 'all'}
      onclick={() => selectedAgendaId = 'all'}
    >
      전체
    </button>
    {#each agendas as agenda (agenda.id)}
      <button
        class="tab-btn"
        class:active={selectedAgendaId === agenda.id}
        onclick={() => selectedAgendaId = agenda.id}
      >
        {agenda.order_num}. {truncate(agenda.title, 12)}
        {#if agenda.time_segments?.length}
          <span class="duration">
            ({formatDuration(getTotalDuration(agenda))})
          </span>
        {/if}
      </button>
    {/each}
  </div>
{/if}
```

### 6.2 총 시간 계산

```typescript
function getTotalDuration(agenda: Agenda): number {
  if (!agenda.time_segments) return 0;
  return agenda.time_segments.reduce((sum, seg) => {
    const end = seg.end ?? 0;
    return sum + (end - seg.start);
  }, 0);
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}초`;
  return `${mins}분 ${secs}초`;
}
```

---

## 7. 상태 전환 다이어그램

```
[녹음 시작]
    │
    ▼
안건1: [{start:0, end:null}]
    │
    │ [안건2 클릭] @ 30초
    ▼
안건1: [{start:0, end:30}]
안건2: [{start:30, end:null}]
    │
    │ [안건3 클릭] @ 60초
    ▼
안건2: [{start:30, end:60}]
안건3: [{start:60, end:null}]
    │
    │ [안건1 클릭] @ 90초 (재방문)
    ▼
안건3: [{start:60, end:90}]
안건1: [{start:0, end:30}, {start:90, end:null}]  ← 두 번째 구간 추가
    │
    │ [녹음 종료] @ 120초
    ▼
안건1: [{start:0, end:30}, {start:90, end:120}]

최종:
- 안건1: 30초 + 30초 = 60초 분량
- 안건2: 30초 분량
- 안건3: 30초 분량
```

---

## 8. 구현 체크리스트

### Phase 1: Backend (DB + API)
- [ ] Alembic 마이그레이션 (`time_segments` JSONB)
- [ ] `models/agenda.py` - 필드 추가
- [ ] `schemas/agenda.py` - TimeSegment, AgendaUpdate, AgendaResponse
- [ ] 마이그레이션 실행

### Phase 2: Frontend 타입
- [ ] `stores/meeting.ts` - TimeSegment, Agenda 타입

### Phase 3: AgendaNotePanel UI 개선
- [ ] 안건 목록 섹션 추가
- [ ] 상태 아이콘 (✓, ▶, ○, ↺)
- [ ] 시간 표시
- [ ] 터치 최적화 (48px 높이)
- [ ] 접기/펼치기 토글

### Phase 4: 안건 전환 로직
- [ ] `handleAgendaChange()` 함수
- [ ] `closeSegment()`, `openSegment()`
- [ ] 녹음 시작/종료 시 처리
- [ ] 이전/다음/목록 클릭 모두 동일 로직

### Phase 5: LLM 처리
- [ ] `get_agenda_transcript()` 수정
- [ ] 여러 구간 합산 로직

### Phase 6: 결과 페이지
- [ ] TranscriptViewer 안건 탭
- [ ] 필터링 로직
- [ ] 총 시간 표시

### Phase 7: 테스트 & 배포
- [ ] 순차 진행 테스트
- [ ] 왔다갔다 테스트
- [ ] 기존 데이터 호환성
- [ ] 프로덕션 배포

---

## 다음 단계

`/pdca do time-segments` 실행하여 구현 시작
