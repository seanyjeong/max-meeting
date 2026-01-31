# MAX Meeting UX/UI 개선 계획

> 레퍼런스: Linear(이슈 관리), Notion(문서 작성), Figma(협업), Cron(캘린더)

---

## 1. 프로젝트 현황 분석

### 1.1 기술 스택
- **Framework**: SvelteKit 2 + Svelte 5 (Runes)
- **Styling**: TailwindCSS + Catppuccin Mocha 다크테마
- **Icons**: Lucide Svelte
- **Drawing**: tldraw
- **Font**: Pretendard (이미 설정됨)

### 1.2 주요 기능
- 회의 CRUD (생성/조회/수정/삭제)
- 계층적 아젠다 관리
- 실시간 녹음 + STT (Speech-to-Text)
- 화이트보드 스케치
- LLM 기반 회의 요약/결과 생성
- 연락처 관리 (PII 암호화)
- 오프라인 지원 (PWA)

### 1.3 현재 UI 특징
- ✅ 기본적인 디자인 시스템 (card, btn, input, badge)
- ✅ 다크모드 지원 (Catppuccin Mocha)
- ✅ 반응형 디자인 (태블릿 최적화)
- ✅ 접근성 고려 (SkipLink, ARIA 레이블)
- ✅ 키보드 단축키 (Quick Jump)
- ⚠️ 시각적 디자인이 기본적 (Linear 수준의 미니멀함 부족)
- ⚠️ 애니메이션이 단순함
- ⚠️ 대시보드 정보 밀도가 낮음

---

## 2. 레퍼런스 분석

### 2.1 Linear (주요 레퍼런스)
**적용 포인트:**
- **미니멀 리스트 뷰**: 회의 목록을 Linear의 이슈 리스트처럼 깔끔하게
- **키보드 중심 네비게이션**: 모든 작업을 키보드로 빠르게
- **미세 인터랙션**: hover 시 subtle한 배경색 변화, 스무스한 전환
- **명령 팔레트 (Cmd+K)**: 빠른 이동/액션 실행
- **사이드바 네비게이션**: 좁고 깔끔한 사이드바

**디자인 특징:**
- Border: 거의 보이지 않음 (배경색 대비로 구분)
- Shadow: 미세한 그림자 (0 1px 3px rgba(0,0,0,0.1))
- Radius: 작은 둥글기 (6-8px)
- Typography: -0.01em letter-spacing, 1.5 line-height
- Spacing: 4px 기반 (4, 8, 12, 16, 24, 32)

### 2.2 Notion (문서 작성)
**적용 포인트:**
- **블록 기반 아젠다**: 안건을 블록 단위로 편집
- **슬래시 커맨드**: "/"로 블록 타입 변경
- **중첩 구조 시각화**: 들여쓰기 + 세로선으로 계층 표현
- **drag-and-drop**: 블록 이동

### 2.3 Figma (협업)
**적용 포인트:**
- **댓글 스레드**: 회의 내용에 댓글 추가
- **실시간 커서**: 동시 편집 표시 (향후 확장)
- **버전 히스토리**: 회의 결과 버전 비교 UI

### 2.4 Cron/Notion Calendar (스케줄링)
**적용 포인트:**
- **캘린더 뷰**: 회의를 캘린더로 시각화
- **타임라인**: 주간/월간 뷰 전환
- **오버랩 표시**: 중복 회의 시각화

---

## 3. 개선 계획

### Phase 1: 디자인 시스템 정리 (1주)

#### 3.1.1 색상 시스템 개선
```css
/* 현재: 기본 Tailwind 색상 */
/* 개선: Linear 스타일의 subtle한 색상 */

--bg-primary: #ffffff;           /* 배경 */
--bg-secondary: #f8f9fa;         /* 카드 배경 */
--bg-tertiary: #f1f3f4;          /* 호버 배경 */
--bg-hover: rgba(0,0,0,0.04);    /* 미세 호버 */

--text-primary: #1a1a1a;         /* 주요 텍스트 */
--text-secondary: #6b7280;       /* 보조 텍스트 */
--text-tertiary: #9ca3af;        /* 힌트 텍스트 */

--border-subtle: rgba(0,0,0,0.08);  /* 거의 안 보이는 볼더 */
--border-default: rgba(0,0,0,0.12); /* 기본 볼더 */

/* 상태 색상 - 채도 낮춤 */
--status-draft: #6b7280;         /* 회색 */
--status-active: #f59e0b;        /* 노랑 - 진행중 */
--status-completed: #10b981;     /* 초록 - 완료 */
--status-cancelled: #ef4444;     /* 빨강 - 취소 */
```

#### 3.1.2 타이포그래피 개선
```css
/* Pretendard 활용 */
font-family: 'Pretendard', -apple-system, sans-serif;

/* 스케일 */
--text-xs: 12px;     line-height: 16px;   /* 뱃지, 라벨 */
--text-sm: 13px;     line-height: 18px;   /* 보조 텍스트 */
--text-base: 14px;   line-height: 20px;   /* 본문 */
--text-lg: 16px;     line-height: 24px;   /* 강조 본문 */
--text-xl: 20px;     line-height: 28px;   /* 섹션 타이틀 */
--text-2xl: 24px;    line-height: 32px;   /* 페이지 타이틀 */

/* 웨이트 */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;

/* 트래킹 */
letter-spacing: -0.01em;  /* 모든 텍스트에 미세하게 */
```

#### 3.1.3 간격 시스템 (4px 기반)
```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
```

#### 3.1.4 컴포넌트 리디자인

**Button (Linear 스타일)**
```svelte
<!-- Primary -->
<button class="btn-primary">
  bg-[#2563eb] hover:bg-[#1d4ed8] text-white
  px-4 py-2 rounded-md text-sm font-medium
  transition-colors duration-150
  active:scale-[0.98]
</button>

<!-- Secondary -->
<button class="btn-secondary">
  bg-transparent hover:bg-black/5 text-gray-700
  border border-gray-200 hover:border-gray-300
  px-4 py-2 rounded-md text-sm font-medium
</button>

<!-- Ghost -->
<button class="btn-ghost">
  bg-transparent hover:bg-black/5 text-gray-600
  px-3 py-1.5 rounded-md text-sm
</button>
```

**Card (subtle한 볼더)**
```svelte
<div class="card">
  bg-white rounded-lg
  border border-gray-100  /* 거의 안 보이는 볼더 */
  shadow-[0_1px_3px_rgba(0,0,0,0.05)]  /* 미세한 그림자 */
  p-4
</div>
```

**Input (Focus Ring 개선)**
```svelte
<input class="input">
  w-full px-3 py-2 bg-white
  border border-gray-200 rounded-md
  text-sm text-gray-900
  placeholder:text-gray-400
  focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500
  transition-all duration-150
</input>
```

**Badge (Pill 스타일)**
```svelte
<!-- Draft -->
<span class="badge-draft">
  bg-gray-100 text-gray-600
  px-2 py-0.5 rounded-full text-xs font-medium
</span>

<!-- In Progress -->
<span class="badge-active">
  bg-amber-50 text-amber-700 ring-1 ring-amber-600/20
  px-2 py-0.5 rounded-full text-xs font-medium
</span>

<!-- Completed -->
<span class="badge-completed">
  bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20
  px-2 py-0.5 rounded-full text-xs font-medium
</span>
```

---

### Phase 2: 대시보드 개선 (1주)

#### 3.2.1 레이아웃 변경
**현재**: 카드 형태의 섹션 구분
**개선**: Linear 스타일의 리스트 중심 레이아웃

```
┌─────────────────────────────────────────────────────┐
│  MAX Meeting                              [+ 새 회의]│
├─────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐│
│  │  🔥 진행 중인 회의                               ││
│  │  [회의 제목]                    [계속하기 →]    ││
│  └─────────────────────────────────────────────────┘│
│                                                     │
│  ┌─────────────────────────────────────────────────┐│
│  │  📅 오늘의 회의 (3)                            ││
│  │                                                 ││
│  │  ○ 아젠다 확정 회의      14:00    회의실 A     ││
│  │  ○ 주간 스탠드업          16:00    Zoom        ││
│  │  ○ 클라이언트 미팅        17:30    (온라인)    ││
│  └─────────────────────────────────────────────────┘│
│                                                     │
│  ┌─────────────────────────────────────────────────┐│
│  │  📝 최근 완료된 회의                            ││
│  │                                                 ││
│  │  ● 신규 기능 기획 회의    01/28    [보고서]    ││
│  │  ● Q1 OKR 리뷰           01/25    [보고서]    ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

#### 3.2.2 새 컴포넌트

**MeetingListItem.svelte**
```svelte
<button class="group flex items-center gap-3 w-full p-3 rounded-lg
               hover:bg-gray-50 transition-colors duration-150
               active:scale-[0.995]">
  <!-- Status Indicator -->
  <div class="w-2 h-2 rounded-full {statusColor}"></div>
  
  <!-- Content -->
  <div class="flex-1 min-w-0 text-left">
    <div class="text-sm font-medium text-gray-900 truncate">
      {meeting.title}
    </div>
    <div class="text-xs text-gray-500 mt-0.5">
      {meeting.meeting_type?.name} · {formatTime(meeting.scheduled_at)}
    </div>
  </div>
  
  <!-- Meta -->
  <div class="flex items-center gap-2">
    <Badge status={meeting.status} />
    <ChevronRight class="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
  </div>
</button>
```

**QuickActions.svelte**
```svelte
<!-- 대시보드 상단에 빠른 액션 -->
<div class="flex gap-2">
  <QuickAction icon={Plus} label="새 회의" shortcut="N" on:click={createMeeting} />
  <QuickAction icon={Mic} label="빠른 녹음" shortcut="R" on:click={quickRecord} />
  <QuickAction icon={FileText} label="템플릿" shortcut="T" on:click={templates} />
</div>
```

---

### Phase 3: 회의 목록 개선 (1주)

#### 3.3.1 Linear 스타일 리스트 뷰
**현재**: 카드 기반
**개선**: 테이블 형태 + 선택 시 사이드 패널

```
┌─────────────────────────────────────────────────────────────┐
│  회의                                  [필터 ▼] [+ 새 회의]  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 🔍 검색...                          [상태 ▼] [검색] │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  제목                    타입        시간          상태       │
│  ───────────────────────────────────────────────────────    │
│  주간 스탠드업           정규       오늘 10:00    진행중   →  │
│  클라이언트 미팅         대외       내일 14:00    예정     →  │
│  Q1 리뷰                 정규       01/30 16:00   완료     →  │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

#### 3.3.2 키보드 네비게이션
```typescript
// MeetingListKeyboard.svelte
// J/K: 위/아래 이동
// Enter: 선택한 회의 열기
// /: 검색 포커스
// N: 새 회의
// E: 수정
// #: 상태 변경
// Cmd+K: 명령 팔레트
```

#### 3.3.3 그룹핑 기능
```svelte
<!-- 날짜별 그룹핑 -->
{#each groupedMeetings as group}
  <div class="group">
    <div class="sticky top-0 bg-white/95 backdrop-blur-sm py-2 px-3 
                text-xs font-medium text-gray-500 uppercase tracking-wider">
      {group.label}  <!-- "오늘", "내일", "이번 주", "이전" -->
    </div>
    <div class="divide-y divide-gray-100">
      {#each group.meetings as meeting}
        <MeetingListItem {meeting} />
      {/each}
    </div>
  </div>
{/each}
```

---

### Phase 4: 회의 상세 페이지 개선 (2주)

#### 3.4.1 3컬럼 레이아웃
```
┌──────────────┬───────────────────────────┬──────────────┐
│  회의 정보   │        메인 콘텐츠         │   사이드    │
│              │                           │   패널      │
├──────────────┼───────────────────────────┼──────────────┤
│              │  [탭: 아젠다 | 녹음 | 결과] │             │
│  📋 안건     │                           │  👥 참석자   │
│  ─────────   │  1. 개요                  │  ─────────  │
│  □ 아젠다 1  │     1.1 세부 안건         │  김OO      │
│  □ 아젠다 2  │     1.2 세부 안건         │  이OO      │
│  □ 아젠다 3  │  2. 논의사항              │             │
│              │     2.1 논의 내용         │  📝 노트     │
│  🎤 녹음     │                           │  ─────────  │
│  [녹음 버튼] │  3. 결론                  │  빠른 메모  │
│              │                           │             │
│  📊 결과     │  ──────────────────────   │  ⏱️ 타이머   │
│  [생성하기]  │                           │  ─────────  │
│              │  [+ 새 안건 추가]         │  00:32:15   │
│              │                           │             │
└──────────────┴───────────────────────────┴──────────────┘
```

#### 3.4.2 아젠다 에디터 (Notion 스타일)
```svelte
<!-- BlockEditor.svelte -->
<div class="editor">
  {#each blocks as block}
    <div class="block group" data-type={block.type}>
      <!-- Drag Handle -->
      <div class="drag-handle opacity-0 group-hover:opacity-100">
        <GripVertical class="w-4 h-4 text-gray-400" />
      </div>
      
      <!-- Content -->
      {#if block.type === 'heading1'}
        <h1 class="text-lg font-semibold" contenteditable>{block.content}</h1>
      {:else if block.type === 'heading2'}
        <h2 class="text-base font-semibold" contenteditable>{block.content}</h2>
      {:else if block.type === 'bullet'}
        <div class="flex gap-2">
          <span class="text-gray-400 mt-1.5">•</span>
          <p contenteditable>{block.content}</p>
        </div>
      {:else if block.type === 'checkbox'}
        <label class="flex gap-2 items-start">
          <input type="checkbox" bind:checked={block.checked} 
                 class="mt-1 rounded border-gray-300" />
          <span class:line-through={block.checked} class:text-gray-400={block.checked}>
            {block.content}
          </span>
        </label>
      {/if}
      
      <!-- Slash Menu Trigger -->
      <div class="slash-menu-trigger">
        "/" 입력 시 메뉴 표시
      </div>
    </div>
  {/each}
</div>
```

#### 3.4.3 슬래시 커맨드 메뉴
```svelte
<!-- SlashMenu.svelte -->
{#if showSlashMenu}
  <div class="slash-menu">
    <div class="category">기본 블록</div>
    <MenuItem icon={Heading1} label="제목 1" shortcut="#" />
    <MenuItem icon={Heading2} label="제목 2" shortcut="##" />
    <MenuItem icon={List} label="글머리 기호" shortcut="-" />
    <MenuItem icon={CheckSquare} label="체크리스트" shortcut="[]" />
    <MenuItem icon={Type} label="텍스트" shortcut="" />
    
    <div class="category">고급</div>
    <MenuItem icon={Clock} label="타이머 삽입" />
    <MenuItem icon={Users} label="참석자 멘션" shortcut="@" />
  </div>
{/if}
```

#### 3.4.4 녹음 인터페이스 개선
```svelte
<!-- RecordingPanel.svelte -->
<div class="recording-panel">
  {#if status === 'idle'}
    <RecordButton 
      on:click={startRecording}
      class="w-16 h-16 rounded-full bg-red-500 text-white 
             hover:bg-red-600 hover:scale-105 transition-all
             shadow-lg shadow-red-500/30"
    />
    <p class="text-sm text-gray-500 mt-4">클릭하여 녹음 시작</p>
    
  {:else if status === 'recording'}
    <div class="recording-active">
      <!-- 파형 시각화 -->
      <WaveformVisualizer {audioData} />
      
      <!-- 타이머 -->
      <div class="timer text-3xl font-mono font-medium">
        {formatDuration(elapsed)}
      </div>
      
      <!-- 컨트롤 -->
      <div class="controls flex gap-3">
        <PauseButton on:click={pauseRecording} />
        <StopButton on:click={stopRecording} class="bg-red-500" />
      </div>
    </div>
  {/if}
</div>
```

---

### Phase 5: 명령 팔레트 개선 (3일)

#### 3.5.1 Linear 스타일 Cmd+K
```svelte
<!-- CommandPalette.svelte -->
{#if open}
  <div class="fixed inset-0 z-50" on:click={close}>
    <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" />
    
    <div class="absolute top-[20%] left-1/2 -translate-x-1/2 w-full max-w-2xl"
         on:click|stopPropagation>
      <div class="bg-white rounded-xl shadow-2xl overflow-hidden">
        <!-- Search Input -->
        <div class="flex items-center px-4 py-3 border-b border-gray-100">
          <Search class="w-5 h-5 text-gray-400" />
          <input
            type="text"
            bind:value={query}
            placeholder="명령어 검색..."
            class="flex-1 ml-3 text-base outline-none placeholder:text-gray-400"
            autofocus
          />
          <kbd class="px-2 py-1 bg-gray-100 rounded text-xs text-gray-500">ESC</kbd>
        </div>
        
        <!-- Results -->
        <div class="max-h-[400px] overflow-y-auto py-2">
          {#each filteredCommands as group}
            <div class="px-4 py-1.5 text-xs font-medium text-gray-500 uppercase">
              {group.category}
            </div>
            {#each group.items as item}
              <button class="w-full flex items-center gap-3 px-4 py-2.5
                           hover:bg-gray-50 transition-colors
                           {selected === item ? 'bg-blue-50 text-blue-600' : 'text-gray-700'}">
                <svelte:component this={item.icon} class="w-4 h-4" />
                <span class="flex-1 text-left text-sm">{item.label}</span>
                {#if item.shortcut}
                  <kbd class="px-1.5 py-0.5 bg-gray-100 rounded text-xs text-gray-500">
                    {item.shortcut}
                  </kbd>
                {/if}
              </button>
            {/each}
          {/each}
        </div>
        
        <!-- Footer -->
        <div class="flex items-center gap-4 px-4 py-2 bg-gray-50 text-xs text-gray-500">
          <span>↑↓ 선택</span>
          <span>↵ 실행</span>
        </div>
      </div>
    </div>
  </div>
{/if}
```

**명령어 목록:**
- **회의**: 새 회의 (N), 회의 검색 (/), 최근 회의
- **액션**: 빠른 녹음 (R), 아젠다 편집 (E), 결과 생성 (G)
- **보기**: 다크모드 토글, 전체화면
- **이동**: 대시보드, 회의 목록, 연락처

---

### Phase 6: 애니메이션 & 인터랙션 (3일)

#### 3.6.1 페이지 전환
```css
/* Linear 스타일의 빠른 전환 */
.page-transition {
  animation: pageEnter 0.15s ease-out;
}

@keyframes pageEnter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 리스트 아이템 등장 */
.list-item-enter {
  animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-8px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
```

#### 3.6.2 미세 인터랙션
```svelte
<!-- Hover 시 subtle한 변화 -->
<button class="transition-all duration-150
               hover:bg-gray-50 hover:translate-x-0.5
               active:scale-[0.98]">

<!-- Focus Ring -->
<input class="focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500
             transition-shadow duration-150">

<!-- Dropdown -->
<div class="origin-top animate-dropdown">
  @keyframes dropdown {
    from { opacity: 0; transform: scaleY(0.95); }
    to { opacity: 1; transform: scaleY(1); }
  }
</div>
```

#### 3.6.3 스켈레톤 로딩 개선
```svelte
<!-- SkeletonPulse.svelte -->
<div class="skeleton">
  <div class="h-4 bg-gray-200 rounded animate-pulse" />
</div>

<style>
  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  
  .skeleton-shimmer {
    background: linear-gradient(90deg, 
      #f1f3f4 25%, 
      #e8eaed 50%, 
      #f1f3f4 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }
</style>
```

---

### Phase 7: 캘린더 뷰 추가 (선택, 1주)

#### 3.7.1 주간/월간 캘린더
```svelte
<!-- CalendarView.svelte -->
<div class="calendar">
  <!-- Header -->
  <div class="flex justify-between items-center mb-4">
    <h2 class="text-lg font-semibold">{currentMonth}</h2>
    <div class="flex gap-2">
      <button on:click={prevMonth}>←</button>
      <button on:click={today}>오늘</button>
      <button on:click={nextMonth}>→</button>
    </div>
  </div>
  
  <!-- Grid -->
  <div class="grid grid-cols-7 gap-1">
    {#each days as day}
      <div class="calendar-day {day.isToday ? 'today' : ''} 
                              {day.hasMeeting ? 'has-meeting' : ''}">
        <span class="day-number">{day.date}</span>
        {#each day.meetings as meeting}
          <div class="meeting-dot" style="background: {meeting.color}"></div>
        {/each}
      </div>
    {/each}
  </div>
</div>
```

---

## 4. 구현 우선순위

### 🔥 P0 (필수)
1. 디자인 시스템 정리 (색상, 타이포그래피, 간격)
2. Button, Input, Card 컴포넌트 리디자인
3. Badge 컴포넌트 개선
4. 대시보드 레이아웃 개선

### ⚡ P1 (중요)
5. 회의 목록 Linear 스타일로 변경
6. 회의 상세 페이지 3컬럼 레이아웃
7. 키보드 네비게이션 구현
8. 명령 팔레트 개선

### ✨ P2 (향상)
9. 아젠다 블록 에디터
10. 슬래시 커맨드
11. 애니메이션 개선
12. 캘린더 뷰

---

## 5. 파일 변경 계획

### 수정 대상
```
frontend/src/
├── app.css                          # 색상 변수 업데이트
├── tailwind.config.js               # 새 색상/간격 추가
├── routes/
│   ├── +page.svelte                 # 대시보드 리디자인
│   ├── meetings/+page.svelte        # 목록 뷰 개선
│   ├── meetings/[id]/+page.svelte   # 상세 페이지 3컬럼
│   └── +layout.svelte               # 사이드바 개선
├── lib/components/
│   ├── ui/
│   │   ├── MeetingCard.svelte       # 카드 디자인 개선
│   │   ├── Badge.svelte             # 새 컴포넌트
│   │   └── CommandPalette.svelte    # 명령 팔레트 개선
│   └── agenda/
│       └── BlockEditor.svelte       # 새 컴포넌트
```

### 새 파일
```
frontend/src/lib/components/
├── ui/
│   ├── MeetingListItem.svelte
│   ├── QuickActions.svelte
│   └── CalendarView.svelte
├── agenda/
│   ├── BlockEditor.svelte
│   ├── SlashMenu.svelte
│   └── DragHandle.svelte
└── layout/
    └── ThreeColumnLayout.svelte
```

---

## 6. 성능 고려사항

- **will-change**: 애니메이션 요소에 적절히 사용
- **content-visibility**: 리스트 아이템에 적용
- **virtual scrolling**: 회의 목록 50+ 개 시
- **lazy loading**: 이미지/아이콘 동적 import

---

## 7. 접근성 체크리스트

- [ ] 키보드 전체 네비게이션 가능
- [ ] Focus indicator 명확히
- [ ] ARIA 레이블 유지
- [ ] Reduced motion 지원
- [ ] Color contrast WCAG 2.1 AA

---

**예상 소요 시간**: 4-5주 (P0+P1 기준)
**담당자**: 프론트엔드 개발자 1명
