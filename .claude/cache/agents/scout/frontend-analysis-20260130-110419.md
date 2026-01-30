# MAX Meeting Frontend Analysis
Generated: 2026-01-30

## Summary
MAX Meeting 프론트엔드는 SvelteKit 2 + Svelte 5 기반의 PWA 회의 관리 앱입니다. 
총 14개 라우트 페이지로 구성되어 있으며, 녹음 → STT → 회의록 생성의 전체 플로우를 지원합니다.

## Project Structure
```
frontend/
├── src/
│   ├── routes/              # SvelteKit 페이지 (14개 파일)
│   │   ├── +layout.svelte   # 전역 레이아웃
│   │   ├── +page.svelte     # 홈페이지
│   │   ├── login/           # 로그인
│   │   ├── contacts/        # 연락처 관리 (목록, 상세, 신규)
│   │   └── meetings/        # 회의 관련 (6개 라우트)
│   │       ├── +page.svelte           # 회의 목록
│   │       ├── new/+page.svelte       # 새 회의 생성
│   │       ├── deleted/+page.svelte   # 삭제된 회의
│   │       ├── [id]/+page.svelte      # 회의 상세
│   │       ├── [id]/record/+page.svelte     # 녹음 페이지
│   │       ├── [id]/sketch/+page.svelte     # 스케치 페이지
│   │       ├── [id]/results/+page.svelte    # 결과 페이지
│   │       └── [id]/results/edit/+page.svelte # 결과 수정
│   │
│   └── lib/
│       ├── components/      # 43개 컴포넌트
│       │   ├── recording/   # 녹음 관련 (7개)
│       │   ├── results/     # 결과 관련 (4개)
│       │   ├── sketch/      # 스케치 관련 (3개)
│       │   └── ui/          # UI 기본 (12개)
│       │
│       └── stores/          # 9개 스토어
```

---

## 1. 라우트 구조

### 회의 관련 라우트 (6개)

| 경로 | 파일 | 주요 기능 |
|------|------|-----------|
| `/meetings` | `meetings/+page.svelte` | 회의 목록, 검색, 필터링 |
| `/meetings/new` | `meetings/new/+page.svelte` | 새 회의 생성 (AI 안건 파싱) |
| `/meetings/deleted` | `meetings/deleted/+page.svelte` | 삭제된 회의 복구 |
| `/meetings/[id]` | `meetings/[id]/+page.svelte` | 회의 상세 보기 |
| `/meetings/[id]/record` | `meetings/[id]/record/+page.svelte` | 녹음 인터페이스 |
| `/meetings/[id]/sketch` | `meetings/[id]/sketch/+page.svelte` | 스케치 전용 |
| `/meetings/[id]/results` | `meetings/[id]/results/+page.svelte` | 결과 조회/생성 |
| `/meetings/[id]/results/edit` | `meetings/[id]/results/edit/+page.svelte` | 결과 수정 |

### 연락처 라우트 (3개)

| 경로 | 기능 |
|------|------|
| `/contacts` | 연락처 목록 |
| `/contacts/new` | 새 연락처 |
| `/contacts/[id]` | 연락처 상세 |

### 기타 라우트 (3개)

| 경로 | 기능 |
|------|------|
| `/` | 홈페이지 |
| `/login` | 로그인 |
| `+layout.svelte` | 전역 레이아웃 (네비게이션, PWA) |

---

## 2. 회의 상세 페이지 (`/meetings/[id]`)

**파일:** `frontend/src/routes/meetings/[id]/+page.svelte`

### 주요 기능
- 회의 정보 표시 (제목, 일시, 장소, 참석자)
- 안건 목록 (계층 구조, 질문 체크리스트)
- 상태별 액션 버튼
  - `draft` → "회의 시작" → `/meetings/{id}/record`로 이동
  - `in_progress` → "회의 계속하기" → `/meetings/{id}/record`로 이동
  - `completed` → "결과 보기" → `/meetings/{id}/result`로 이동 (오타 있음: `/results`가 맞음)
- 오프라인 캐시 지원 (10초 타임아웃, 캐시 fallback)

### 핵심 코드 흐름
```svelte
onMount(() => {
  loadMeeting(); // API GET /meetings/{id}
});

async function startMeeting() {
  // PATCH /meetings/{id} { status: 'in_progress' }
  goto(`/meetings/${meetingId}/record`);
}
```

### 상태별 UI
```svelte
{#if $currentMeeting.status === 'draft'}
  <button onclick={startMeeting}>회의 시작</button>
{:else if $currentMeeting.status === 'in_progress'}
  <a href="/meetings/{meetingId}/record">회의 계속하기</a>
{:else if $currentMeeting.status === 'completed'}
  <a href="/meetings/{meetingId}/result">결과 보기</a>  <!-- 버그: /results가 맞음 -->
{/if}
```

**주목할 점:**
- **회의 마무리/완료 버튼 없음** - 상태 변경은 자동 또는 다른 경로에서 처리
- 결과 페이지 링크 오타: `/result` → `/results`로 수정 필요

---

## 3. 녹음 페이지 (`/meetings/[id]/record`)

**파일:** `frontend/src/routes/meetings/[id]/record/+page.svelte`

### 레이아웃 구조
```
┌──────────────────────────────────────────┐
│ Navigation Bar (64px)                    │
├──────────────────────────────────────────┤
│ CompactRecordingBar (56px) - Fixed Top   │
│ - [녹음 버튼] 00:00 [파형] [현재 안건]      │
├──────────────────────────────────────────┤
│ Breadcrumb (52px)                        │
├──────────────────────────────────────────┤
│ Split Layout (100vh - 172px)             │
│ ┌────────┬──────────────────────────┐    │
│ │ 25%    │ 75%                      │    │
│ │ Agenda │ Note/Sketch Area         │    │
│ │ Panel  │ [텍스트 | 스케치] 탭      │    │
│ └────────┴──────────────────────────┘    │
└──────────────────────────────────────────┘
```

### 핵심 컴포넌트

#### 1. CompactRecordingBar (고정 상단바)
**파일:** `frontend/src/lib/components/recording/CompactRecordingBar.svelte`

```svelte
<div class="fixed top-16 left-0 right-0 z-40 h-14">
  <!-- LEFT: 녹음/중지 버튼, 타이머, 미니 파형 -->
  <button onclick={handleRecordButtonClick}>
    {#if isRecording} [중지 아이콘] {:else} [녹음 아이콘] {/if}
  </button>
  <div class="timer">{formatTime(recordingTime)}</div>
  <div class="waveform">{#each waveformBars as bar} ... {/each}</div>
  
  <!-- CENTER: 일시정지/재개 버튼 -->
  {#if isActive}
    <button onclick={handlePauseClick}>[일시정지/재개]</button>
  {/if}
  
  <!-- RIGHT: 현재 안건 표시 -->
  <span>현재 안건: {currentAgenda}</span>
</div>
```

**특징:**
- 56px 고정 높이, 브루탈리스트 디자인
- 녹음 중: 빨간 테두리 + 파형 애니메이션
- 일시정지: 노란 테두리

#### 2. AgendaNotePanel (왼쪽 25%)
**파일:** `frontend/src/lib/components/recording/AgendaNotePanel.svelte`

```svelte
<div class="w-1/4 border-r">
  <!-- 안건 진행도 표시 -->
  <div>안건 {currentAgendaIndex + 1} / {agendas.length}</div>
  
  <!-- 현재 안건 상세 -->
  <h2>{currentAgenda.title}</h2>
  <p>{currentAgenda.description}</p>
  
  <!-- 질문 체크리스트 -->
  {#if totalQuestions > 0}
    {#each currentAgenda.questions as question}
      <input type="checkbox" bind:checked={question.answered} />
      <span>{question.question}</span>
    {/each}
  {/if}
  
  <!-- 메모 입력 -->
  <textarea bind:value={noteContent} oninput={handleNoteInput}></textarea>
  
  <!-- 이전/다음 버튼 -->
  <button onclick={goToPrevAgenda}>이전</button>
  <button onclick={goToNextAgenda}>다음</button>
</div>
```

**기능:**
- 안건별 메모 자동 저장 (500ms debounce)
- 질문 체크박스 토글
- 안건 간 이동 (이전/다음)

#### 3. NoteSketchArea (오른쪽 75%)
**파일:** `frontend/src/lib/components/recording/NoteSketchArea.svelte`

```svelte
<div class="flex-1">
  <!-- 탭 전환 -->
  <button onclick={() => activeTab = 'text'}>텍스트</button>
  <button onclick={() => activeTab = 'sketch'}>스케치</button>
  
  {#if activeTab === 'text'}
    <textarea bind:value={textContent} oninput={onTextChange}></textarea>
  {:else}
    <TldrawWrapper bind:snapshot={sketchSnapshot} onchange={onSketchChange} />
  {/if}
</div>
```

### 녹음 플로우

```
1. [녹음 시작] handleStartRecording()
   → recordingStore.start(meetingId)
   → visualizationStore.start(mediaRecorder)
   → 첫 안건 started_at_seconds 업데이트

2. [녹음 중]
   → 청크 업로드 (IndexedDB 저장)
   → 파형 실시간 표시
   → 배터리 모니터링

3. [중지] handleStopRecording()
   → recordingGuard.checkMinimumDuration() (3초 체크)
   → recordingStore.stop() → Blob 생성
   → previewModal 표시 (10초 미리듣기)

4. [업로드 확인] handleConfirmRecording()
   → recordingStore.uploadRecording(meetingId, blob)
   → 청크 단위 업로드 (진행률 표시)
   → goto(`/meetings/${meetingId}/results`)
```

### 복구 기능
```svelte
onMount(async () => {
  hasRecoveryData = await hasUnsavedRecordings(meetingId);
  if (hasRecoveryData) {
    showRecoveryModal = true; // "미저장 녹음 발견" 모달
  }
});

async function handleRecoverRecording() {
  const blob = await combineRecordingChunks(meetingId);
  // → 미리듣기 모달로 이동
}
```

---

## 4. 결과 페이지 (`/meetings/[id]/results`)

**파일:** `frontend/src/routes/meetings/[id]/results/+page.svelte`

### 상태별 UI 플로우

#### 상태 1: 녹음 없음 (no_recordings)
```svelte
<EmptyState>
  <h3>녹음이 없습니다</h3>
  <p>안건과 메모만으로 회의록을 생성하거나, 녹음을 추가할 수 있습니다.</p>
  <Button onclick={handleGenerate}>메모로 회의록 생성</Button>
  <Button onclick={() => goto(`/meetings/${meetingId}/record`)}>녹음하기</Button>
</EmptyState>
```

#### 상태 2: 업로드 완료 (uploaded)
```svelte
<EmptyState>
  <h3>녹음 업로드 완료</h3>
  <p>음성을 텍스트로 변환하려면 아래 버튼을 눌러주세요.</p>
  <Button onclick={triggerSTT}>텍스트 변환 시작</Button>
</EmptyState>
```

#### 상태 3: 변환 중 (processing)
```svelte
<EmptyState>
  <Loader2 class="animate-spin" />
  <h3>음성을 텍스트로 변환 중...</h3>
  <p>자동으로 새로고침됩니다...</p>
</EmptyState>
```
- 3초마다 폴링 (`statusPollInterval`)
- 완료 시 토스트 알림 + transcript 리로드

#### 상태 4: 변환 완료 (ready)
```svelte
<EmptyState>
  <h3>변환 완료!</h3>
  <p>회의록을 생성할 수 있습니다.</p>
  <Button onclick={handleGenerate}>회의록 생성</Button>
</EmptyState>
```

#### 상태 5: 회의록 생성 완료 (hasResult)
```svelte
<!-- 탭 UI -->
<Tabs activeTab={activeTab}>
  <Tab id="summary">요약</Tab>
  <Tab id="actions">실행 항목</Tab>
  <Tab id="transcript">대화 내용</Tab>
</Tabs>

<!-- 액션 버튼 -->
<Button onclick={handleCopyToClipboard}>클립보드 복사</Button>
<Button onclick={handleExportPdf}>PDF 내보내기</Button>
<Button onclick={handleRegenerate}>재생성</Button>
<Button onclick={handleEdit}>수정</Button>
<Button onclick={handleVerify}>검증</Button>
```

### 핵심 함수

```typescript
// STT 트리거
async function triggerSTT() {
  const uploadedRecording = recordings.find(r => r.status === 'uploaded');
  await api.post(`/recordings/${uploadedRecording.id}/process`, {});
  // → 폴링 시작
}

// 회의록 생성
async function handleGenerate() {
  await resultsStore.generateResult(meetingId);
  // POST /meetings/{id}/results
}

// 재생성 (새 버전)
async function handleRegenerate() {
  if (confirm('새 버전을 생성합니다. 계속하시겠습니까?')) {
    await resultsStore.regenerateResult(meetingId);
  }
}

// 검증 완료 표시
async function handleVerify() {
  if (confirm('이 회의 결과를 검증 완료로 표시하시겠습니까?')) {
    await resultsStore.verifyResult(meetingId);
  }
}
```

### 폴링 로직
```typescript
onMount(async () => {
  await loadRecordingsStatus();
  
  // processing 또는 uploaded 상태면 폴링 시작
  if (processingStatus === 'processing' || processingStatus === 'uploaded') {
    statusPollInterval = setInterval(async () => {
      await loadRecordingsStatus();
      if (processingStatus === 'ready') {
        await resultsStore.loadTranscript(meetingId);
        toast.success('변환 완료!');
        clearInterval(statusPollInterval);
      }
    }, 3000);
  }
});
```

---

## 5. 녹음 관련 컴포넌트

### RecordButton.svelte (단독 버튼)
**파일:** `frontend/src/lib/components/recording/RecordButton.svelte`

```svelte
<!-- 80px 큰 버튼 (태블릿 터치 최적화) -->
<button class="w-recording h-recording rounded-full">
  {#if $isRecording}
    <div class="w-8 h-8 bg-white rounded-sm"></div> <!-- 중지 아이콘 -->
    <span class="animate-ping"></span> <!-- 펄스 링 -->
  {:else if $isPaused}
    <svg>재개 아이콘</svg>
  {:else}
    <div class="w-6 h-6 bg-white rounded-full"></div> <!-- 녹음 아이콘 -->
  {/if}
</button>

<!-- 일시정지 버튼 -->
{#if $isRecording || $isPaused}
  <button>일시정지/재개</button>
{/if}

<!-- 타이머 -->
<div class="text-2xl font-mono">{formatTime($recordingTime)}</div>
```

### RecordingGuard.svelte (네비게이션 보호)
**파일:** `frontend/src/lib/components/recording/RecordingGuard.svelte`

```typescript
// 녹음 중 페이지 이탈 방지
beforeNavigate(({ cancel }) => {
  if ($isRecording) {
    if (!confirm('녹음 중입니다. 페이지를 나가시겠습니까?')) {
      cancel();
    } else {
      onConfirmLeave?.();
    }
  }
});

// 최소 녹음 시간 체크 (3초)
function checkMinimumDuration(): boolean {
  if ($recordingTime < 3) {
    if (!confirm('녹음 시간이 3초 미만입니다. 중지하시겠습니까?')) {
      return false;
    }
  }
  return true;
}
```

### Waveform.svelte (파형 시각화)
**파일:** `frontend/src/lib/components/recording/Waveform.svelte`

- Canvas 기반 실시간 파형 렌더링
- 48개 바, 0-255 정규화

### AgendaTracker.svelte (안건 추적기)
**사용 안 됨** - AgendaNotePanel이 대체

---

## 6. 회의 마무리/완료 관련 기능

### 현재 상태 분석

**회의 상태 변경 지점:**

1. **회의 시작** (`draft` → `in_progress`)
   - 위치: `/meetings/[id]` 페이지
   - 트리거: "회의 시작" 버튼
   ```typescript
   async function startMeeting() {
     await api.patch(`/meetings/${meetingId}`, { status: 'in_progress' });
     goto(`/meetings/${meetingId}/record`);
   }
   ```

2. **회의 완료** (`in_progress` → `completed`)
   - **UI에 명시적인 "회의 마무리" 버튼 없음**
   - 추정: 백엔드에서 회의록 생성 시 자동 변경?
   - 또는 관리자가 수동으로 변경?

### 발견된 문제점

#### 문제 1: 회의 마무리 버튼 부재
- 녹음 페이지 (`/record`)에 "녹음 종료 및 회의 마무리" 버튼 없음
- 녹음 중지 → 업로드 → 결과 페이지 이동은 되지만, 회의 상태는 `in_progress` 유지
- 사용자가 회의를 끝내는 명시적인 액션이 없음

#### 문제 2: 결과 페이지 링크 오타
```svelte
<!-- /meetings/[id]/+page.svelte:253 -->
{:else if $currentMeeting.status === 'completed'}
  <a href="/meetings/{meetingId}/result">결과 보기</a>  <!-- 버그 -->
  <!-- 올바른 경로: /meetings/{meetingId}/results -->
{/if}
```

#### 문제 3: 녹음 없이 회의 완료 시나리오
- 결과 페이지에서 "메모로 회의록 생성" 가능
- 하지만 생성 후 회의 상태 변경 로직이 명확하지 않음

### 추천 개선 사항

1. **녹음 페이지에 "회의 마무리" 버튼 추가**
   ```svelte
   <!-- CompactRecordingBar 또는 AgendaNotePanel에 추가 -->
   {#if !$isRecording}
     <Button onclick={handleFinishMeeting}>회의 마무리</Button>
   {/if}
   
   async function handleFinishMeeting() {
     if (confirm('회의를 마무리하시겠습니까?')) {
       await api.patch(`/meetings/${meetingId}`, { status: 'completed' });
       goto(`/meetings/${meetingId}/results`);
     }
   }
   ```

2. **결과 페이지에서도 완료 버튼 제공**
   ```svelte
   <!-- /meetings/[id]/results/+page.svelte -->
   {#if $currentMeeting.status === 'in_progress'}
     <Button onclick={handleCompleteMeeting}>회의 완료 처리</Button>
   {/if}
   ```

3. **경로 오타 수정**
   ```diff
   - <a href="/meetings/{meetingId}/result">결과 보기</a>
   + <a href="/meetings/{meetingId}/results">결과 보기</a>
   ```

---

## 7. UX 플로우 정리

### 전체 플로우 (이상적인 케이스)

```
1. [새 회의 생성] /meetings/new
   → 제목, 유형, 안건 입력 (AI 파싱)
   → 참석자 선택
   → POST /meetings → draft 상태

2. [회의 시작] /meetings/{id}
   → "회의 시작" 버튼 클릭
   → PATCH /meetings/{id} { status: 'in_progress' }
   → 자동 이동: /meetings/{id}/record

3. [녹음 진행] /meetings/{id}/record
   → 녹음 시작/중지
   → 안건별 메모 작성
   → 질문 체크박스 토글
   → 업로드 → 결과 페이지로 이동

4. [결과 조회] /meetings/{id}/results
   → 녹음 상태 확인 (uploaded/processing/ready)
   → STT 트리거 (필요 시)
   → 변환 완료 대기 (폴링)
   → "회의록 생성" 버튼 클릭
   → LLM 요약 생성 (POST /meetings/{id}/results)

5. [회의록 확인] /meetings/{id}/results
   → 요약, 실행 항목, 대화 내용 탭
   → PDF 내보내기, 클립보드 복사
   → 수정 (/meetings/{id}/results/edit)
   → 검증 완료 표시

6. [회의 완료] ❌ 명시적 버튼 없음
   → 현재: 회의 상태가 'completed'로 자동 변경?
   → 추천: "회의 마무리" 버튼 추가 필요
```

### 실제 사용자 경험 문제점

1. **회의 끝내는 방법이 모호함**
   - 녹음 중지 후 "이제 뭐 하지?"
   - 결과 페이지 가면 되는데, 회의가 '완료'된 건지 불명확

2. **상태 표시가 일관되지 않음**
   - 상세 페이지: `in_progress` → "회의 계속하기" 버튼
   - 녹음 없이 결과 생성 가능 → 상태 변화 추적 어려움

3. **녹음 후 자동 이동이 결과 페이지로만**
   - 녹음만 하고 나중에 회의록 생성하고 싶을 수도 있음
   - 중간 확인 단계 필요

---

## 8. 컴포넌트 카테고리

### 녹음 관련 (7개)
| 컴포넌트 | 용도 |
|---------|------|
| RecordButton.svelte | 단독 녹음 버튼 (80px, 터치 최적화) |
| CompactRecordingBar.svelte | 녹음 상태 바 (56px 고정) |
| AgendaNotePanel.svelte | 안건 목록 + 메모 (왼쪽 패널) |
| NoteSketchArea.svelte | 텍스트/스케치 영역 (오른쪽) |
| Waveform.svelte | 파형 시각화 |
| RecordingGuard.svelte | 페이지 이탈 보호 |
| AgendaTracker.svelte | (미사용) |

### 결과 관련 (4개)
| 컴포넌트 | 용도 |
|---------|------|
| SummaryEditor.svelte | 회의 요약 편집기 |
| ActionItems.svelte | 실행 항목 목록 |
| TranscriptViewer.svelte | 대화 내용 표시 |
| SpeakerMapper.svelte | 화자 매핑 (SPEAKER_00 → 실명) |

### UI 기본 (12개)
| 컴포넌트 | 용도 |
|---------|------|
| MeetingCard.svelte | 회의 카드 (목록) |
| ConfirmDialog.svelte | 확인 다이얼로그 |
| RecordingStatus.svelte | 녹음 상태 뱃지 |
| Tabs.svelte | 탭 UI |
| Skeleton.svelte | 로딩 스켈레톤 |
| EmptyState.svelte | 빈 상태 플레이스홀더 |
| KeyboardShortcuts.svelte | 키보드 단축키 핸들러 |
| ErrorBoundary.svelte | 에러 경계 |
| ToastV2.svelte | 토스트 알림 |
| ToastContainerV2.svelte | 토스트 컨테이너 |
| OfflineIndicator.svelte | 오프라인 표시기 |
| (2개 더) | ... |

### 스케치 관련 (3개)
| 컴포넌트 | 용도 |
|---------|------|
| TldrawWrapper.svelte | tldraw 라이브러리 래퍼 |
| SketchPad.svelte | 간단한 스케치 패드 |
| SketchToolbar.svelte | 스케치 도구 모음 |

### 기타 공통 (17개)
- Card, Modal, Badge, Button, Input
- Breadcrumb, LoadingSpinner
- AgendaEditor
- DarkModeToggle
- SyncConflictDialog
- OfflineSyncManager
- QuickJump
- PreflightCheck
- UpdateNotifier
- SkipLink
- Toast, ToastContainer

---

## 9. 스토어 구조 (9개)

| 스토어 | 파일 | 주요 상태 |
|-------|------|----------|
| meeting | stores/meeting.ts | currentMeeting, meetings, isLoading |
| recording | stores/recording.ts | isRecording, isPaused, recordingTime, batteryWarning |
| results | stores/results.ts | currentResult, actionItems, transcriptSegments |
| notes | stores/notes.ts | notes (Map<agendaId, note>) |
| toast | stores/toast.ts | toasts[] |
| offlineCache | stores/offlineCache.ts | 캐시 관리 함수들 |
| visualization | stores/visualization.ts | analyserData (Uint8Array) |
| (2개 더) | ... | ... |

---

## 10. 주요 발견 사항

### 긍정적인 점
1. **체계적인 라우팅** - 회의 생명주기를 잘 반영
2. **오프라인 지원** - IndexedDB 캐싱, PWA
3. **실시간 피드백** - 파형, 배터리, 타이머
4. **AI 통합** - 안건 파싱, 질문 생성, 회의록 요약
5. **접근성** - 키보드 단축키, 터치 최적화 (iPad)

### 개선 필요 사항
1. **회의 마무리 플로우 불명확** ⭐ 핵심 문제
   - "회의 마무리" 버튼 부재
   - 상태 변경 로직 추적 어려움

2. **결과 페이지 경로 오타** (`/result` → `/results`)

3. **상태 폴링 중복**
   - `results/+page.svelte`에서 3초마다 폴링
   - WebSocket으로 개선 가능

4. **에러 핸들링 일관성**
   - 일부 컴포넌트는 console.error만
   - toast 알림 부재

5. **녹음 복구 UX**
   - 복구 모달이 갑자기 떠서 당황스러울 수 있음
   - "이전 녹음 계속하기" 옵션 제공 고려

---

## 11. 파일 경로 참조

### 핵심 파일 (절대 경로)
```
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/[id]/+page.svelte
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/[id]/record/+page.svelte
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/[id]/results/+page.svelte
/home/et/max-ops/max-meeting/frontend/src/lib/components/recording/CompactRecordingBar.svelte
/home/et/max-ops/max-meeting/frontend/src/lib/components/recording/AgendaNotePanel.svelte
/home/et/max-ops/max-meeting/frontend/src/lib/components/recording/RecordButton.svelte
/home/et/max-ops/max-meeting/frontend/src/lib/stores/recording.ts
/home/et/max-ops/max-meeting/frontend/src/lib/stores/results.ts
```

### 라우트 목록
```
/home/et/max-ops/max-meeting/frontend/src/routes/+page.svelte                    # 홈
/home/et/max-ops/max-meeting/frontend/src/routes/+layout.svelte                  # 레이아웃
/home/et/max-ops/max-meeting/frontend/src/routes/login/+page.svelte              # 로그인
/home/et/max-ops/max-meeting/frontend/src/routes/contacts/+page.svelte           # 연락처 목록
/home/et/max-ops/max-meeting/frontend/src/routes/contacts/new/+page.svelte       # 새 연락처
/home/et/max-ops/max-meeting/frontend/src/routes/contacts/[id]/+page.svelte      # 연락처 상세
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/+page.svelte           # 회의 목록
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/new/+page.svelte       # 새 회의
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/deleted/+page.svelte   # 삭제된 회의
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/[id]/+page.svelte      # 회의 상세
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/[id]/record/+page.svelte         # 녹음
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/[id]/sketch/+page.svelte         # 스케치
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/[id]/results/+page.svelte        # 결과
/home/et/max-ops/max-meeting/frontend/src/routes/meetings/[id]/results/edit/+page.svelte   # 결과 수정
```

---

## 12. 권장 조치 사항

### 즉시 수정 (버그)
1. 결과 페이지 링크 오타 수정
   ```diff
   # /meetings/[id]/+page.svelte:253
   - <a href="/meetings/{meetingId}/result">결과 보기</a>
   + <a href="/meetings/{meetingId}/results">결과 보기</a>
   ```

### 단기 개선 (UX 향상)
1. **"회의 마무리" 버튼 추가**
   - 위치: `CompactRecordingBar` 또는 `AgendaNotePanel`
   - 기능: PATCH `/meetings/{id}` { status: 'completed' }
   - 조건: 녹음 중이 아닐 때만 활성화

2. **결과 페이지에서도 완료 버튼 제공**
   - 위치: `results/+page.svelte` 헤더
   - 조건: `$currentMeeting.status === 'in_progress'`

3. **상태 변경 피드백 강화**
   - 회의 시작: "회의가 시작되었습니다" 토스트
   - 회의 완료: "회의가 완료되었습니다" 토스트
   - 상태 뱃지 색상 강조

### 중기 개선 (기능 추가)
1. **WebSocket 기반 실시간 업데이트**
   - 폴링 대신 서버 푸시
   - STT 진행률 실시간 표시

2. **녹음 중간 저장 UI**
   - "임시 저장" 버튼
   - 나중에 이어서 녹음 가능

3. **회의 상태 타임라인**
   - 언제 시작했고, 언제 녹음했고, 언제 완료했는지
   - 감사 로그 개념

---

## 결론

MAX Meeting 프론트엔드는 **잘 구조화된 회의 관리 앱**이지만, 
**회의를 "마무리"하는 명시적인 UX가 부족**합니다.

핵심 개선 사항:
1. "회의 마무리" 버튼 추가 (녹음 페이지 또는 결과 페이지)
2. 결과 페이지 경로 오타 수정 (`/result` → `/results`)
3. 상태 변경 피드백 강화 (토스트 알림)

현재는 녹음 → 업로드 → 결과 조회까지는 매끄럽지만,
**"이제 회의를 끝냈으니 어떻게 마무리하지?"**라는 의문이 남습니다.
