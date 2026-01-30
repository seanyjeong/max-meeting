# UX 개선 및 버그 수정 v1.4 - 상세 설계

> 작성일: 2026-01-30
> Plan 문서: `docs/01-plan/features/ux-improvements-v1.4.plan.md`

---

## Phase 1: Critical 버그 수정

### C1: 자식안건 생성 안됨 🔴 ROOT CAUSE 발견

#### 현재 문제
회의 생성 시 `/meetings/new/+page.svelte`에서 자식안건(children)이 API에 전송되지 않음.

**버그 위치**: `frontend/src/routes/meetings/new/+page.svelte:358-365`

```typescript
// 현재 코드 (버그)
for (let i = 0; i < validAgendas.length; i++) {
    await api.post(`/meetings/${meetingId}/agendas`, {
        title: validAgendas[i].title.trim(),
        description: validAgendas[i].description.trim() || null,
        order_num: i + 1
        // ❌ children 필드 누락!
    });
}
```

#### 해결 방안
재귀적으로 자식안건까지 저장하는 함수 작성

```typescript
async function saveAgendasRecursively(
    meetingId: number,
    agendas: ParsedAgendaItem[],
    parentId: number | null = null
) {
    for (let i = 0; i < agendas.length; i++) {
        const agenda = agendas[i];

        // 안건 생성
        const response = await api.post<AgendaResponse>(
            `/meetings/${meetingId}/agendas`,
            {
                title: agenda.title.trim(),
                description: agenda.description?.trim() || null,
                order_num: i + 1,
                parent_id: parentId  // 부모 ID 전달
            }
        );

        // 자식안건 재귀 저장
        if (agenda.children && agenda.children.length > 0) {
            await saveAgendasRecursively(meetingId, agenda.children, response.id);
        }
    }
}
```

---

### C2: 자식안건 숫자 표기

#### 현재 문제
자식안건에 번호가 없거나 "설명"으로만 표시됨

#### 변경 파일
- `frontend/src/routes/meetings/[id]/+page.svelte`

#### 설계

**회의 상세 페이지 - 안건 목록**
```
1. 대안건 제목
   1.1 자식안건 1
   1.2 자식안건 2
2. 대안건 제목 2
```

```svelte
{#each agenda.children as child, childIdx}
    <span class="child-number">{idx + 1}.{childIdx + 1}</span>
    <span>{child.title}</span>
{/each}
```

---

### C3: 안건별 토론 불일치

#### 현재 문제
`안건별 토론` 탭의 내용이 실제 안건과 매칭되지 않음

#### 원인 분석
LLM 회의록 생성 시 `agenda_discussions` 생성 로직 확인 필요

**확인 파일**: `backend/app/services/result.py`

#### 해결 방안
1. LLM 프롬프트에 안건 ID와 제목 명확히 전달
2. 응답에서 agenda_id 기반 매핑
3. 자식안건도 별도 토론 항목으로 생성

---

### C4: PDF 자식안건 없음

#### 현재 문제
`/results/report` 페이지에서 자식안건이 표시되지 않음

#### 확인 사항
- `getDiscussion(child.id)` 함수 호출 시 데이터 없음
- `$resultsStore.agendaDiscussions`에 자식안건 토론 누락

#### 해결 방안
C3 해결 후 자동 해결될 가능성 높음.
추가로 데이터가 없어도 자식안건 제목은 표시하도록 수정.

---

## Phase 2: UX 개선

### U1: 진행 게이지

#### 현재 상태
- STT 처리: `processing` 상태에서 "처리 중..." 텍스트만 표시
- 회의록 생성: `isGenerating` 상태에서 무한 pulse 애니메이션

#### 설계

**STT 진행률** (백엔드 지원 필요)
```typescript
// 옵션 1: 청크 기반 진행률
// recordings 테이블에 processed_chunks / total_chunks 추가

// 옵션 2: 시간 기반 추정
// duration_seconds 기반 예상 시간 계산 (약 1:10 비율)
const estimatedTime = recording.duration_seconds * 10; // 10배 시간 예상
```

**프론트엔드 UI**
```svelte
<div class="progress-bar">
    <div class="progress-fill" style="width: {progress}%"></div>
</div>
<span class="progress-text">{progress}% 완료</span>
```

#### 간단한 대안 (시간 기반)
```typescript
let startTime = Date.now();
let estimatedDuration = 60000; // 1분 예상

$: elapsed = Date.now() - startTime;
$: progress = Math.min(95, (elapsed / estimatedDuration) * 100);
```

---

### U2: 대화내용 탭 UI 색상

#### 현재 문제
선택된 안건 탭이 흰색으로 구분이 어려움

#### 변경 파일
- `frontend/src/lib/components/results/TranscriptViewer.svelte`

#### 설계
```css
/* 기존 */
.agenda-tab.active {
    background: white;
    color: #1d4ed8;
}

/* 개선 */
.agenda-tab.active {
    background: #1d4ed8;  /* 파란색 배경 */
    color: white;
    font-weight: 600;
    box-shadow: 0 2px 4px rgba(29, 78, 216, 0.3);
}
```

---

### U3: 질문 수정/삭제 UI

#### 현재 상태
회의 상세 페이지에서 질문 수정/삭제 UI 없음
(API는 존재: `PATCH /questions/{id}`, `DELETE /questions/{id}`)

#### 변경 파일
- `frontend/src/routes/meetings/[id]/+page.svelte`

#### 설계
```svelte
{#each child.questions as question}
    <div class="question-item">
        <span>{question.question}</span>
        <div class="question-actions">
            <button onclick={() => editQuestion(question)}>
                <Pencil size={14} />
            </button>
            <button onclick={() => deleteQuestion(question.id)}>
                <Trash2 size={14} />
            </button>
        </div>
    </div>
{/each}
```

---

### U4: 회의 시작 통합

#### 현재 상태
회의 상세에서 "녹음 회의", "텍스트만 회의" 분리

#### 설계
단일 "회의 시작" 버튼 → 녹음 페이지에서 모드 선택 (또는 자동)

```svelte
<!-- 기존 -->
<Button onclick={() => goto(`/meetings/${meeting.id}/record`)}>녹음 회의</Button>
<Button onclick={() => goto(`/meetings/${meeting.id}/record?mode=text`)}>텍스트만</Button>

<!-- 개선 -->
<Button onclick={() => goto(`/meetings/${meeting.id}/record`)}>
    회의 시작
</Button>
```

녹음 페이지에서 녹음 버튼 클릭 여부로 자동 판단.

---

### U5: 타이핑 Shift 고정 버그

#### 현재 문제
메모 입력 시 Shift가 눌린 것처럼 대문자가 입력됨

#### 확인 필요
- `frontend/src/lib/components/recording/AgendaNotePanel.svelte`
- `frontend/src/routes/meetings/[id]/record/+page.svelte`

#### 가능한 원인
1. CSS `text-transform: uppercase`
2. 키보드 이벤트 핸들러에서 Shift 상태 잘못 처리
3. `e.preventDefault()` 누락

---

### U6: 빠른이동 제거

#### 현재 상태
녹음 페이지 상단에 "빠른이동" 네비게이션 존재

#### 변경 파일
- `frontend/src/routes/meetings/[id]/record/+page.svelte`

#### 설계
해당 UI 요소 제거 또는 조건부 숨김

---

## Phase 3: 레이아웃

### L1: 녹음 버튼 위치

#### 현재 상태
녹음 버튼이 화면 하단에 떠있는 느낌

#### 설계
녹음 컨트롤을 메인 회의 영역 내부로 통합

```
┌─────────────────────────────────────┐
│ 회의: 제목                          │
├─────────────────────────────────────┤
│ [안건 패널] │ [메모/필기 영역]      │
│             │                       │
│             ├───────────────────────┤
│             │ 🔴 녹음 | ⏸️ 일시정지  │ ← 영역 내부
│             │ 00:15:30              │
└─────────────────────────────────────┘
```

---

### L2: 태블릿 반응형 (2000x1200)

#### 현재 문제
11인치 태블릿 (2000x1200)에서 화면이 작게 보임

#### 설계
미디어 쿼리 추가 및 최소 너비 조정

```css
/* 고해상도 태블릿 */
@media (min-width: 1200px) and (max-width: 2000px) {
    .recording-page {
        font-size: 1.1rem;
    }

    .agenda-panel {
        min-width: 350px;
    }

    .note-area {
        min-height: 500px;
    }
}
```

---

## 구현 순서

```
1. C1: 자식안건 생성 (ROOT CAUSE) - 30분
2. C2: 자식안건 숫자 표기 - 15분
3. C3: 안건별 토론 매칭 - 60분 (백엔드 조사 필요)
4. C4: PDF 자식안건 - 15분
5. U1: 진행 게이지 - 30분
6. U2: 탭 UI 색상 - 10분
7. U3: 질문 수정/삭제 - 30분
8. U4: 회의 시작 통합 - 15분
9. U5: Shift 버그 - 20분
10. U6: 빠른이동 제거 - 5분
11. L1: 녹음 버튼 통합 - 30분
12. L2: 태블릿 반응형 - 20분
```

**총 예상: 약 4-5시간**

---

## 다음 단계

`/pdca do ux-improvements-v1.4` 로 구현 시작
