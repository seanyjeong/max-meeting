# Transcript-Agenda Rematch 기능 설계

> **요약**: LLM 기반으로 대화 내용을 분석하여 잘못 매칭된 안건을 제안/수정하는 기능
>
> **날짜**: 2026-01-31
> **상태**: Design
> **Plan 문서**: [transcript-agenda-rematch.plan.md](../../01-plan/features/transcript-agenda-rematch.plan.md)

---

## 1. 개요

### 1.1 문제 정의

현재 시스템은 **타임스탬프 기반**으로 대화 세그먼트를 안건에 매칭합니다.

```
[안건1 클릭] → 녹음 시작
사용자: "1억 원 장학금 이벤트에 대해서..."  ← 실제론 안건2 내용
→ time_segments 기준으로 안건1에 배치됨 ❌
```

### 1.2 해결 방안

LLM이 대화 **내용**과 **안건 제목/설명**을 비교하여 불일치 감지 시 제안.

---

## 2. 데이터 모델

### 2.1 DB 스키마 변경

**transcripts 테이블의 segments JSONB 구조 확장:**

```json
// 기존
{
  "start": 4.41,
  "end": 11.46,
  "text": "대치종로 X 맥스체대입시",
  "speaker_label": "화자"
}

// 변경 후
{
  "start": 4.41,
  "end": 11.46,
  "text": "대치종로 X 맥스체대입시",
  "speaker_label": "화자",
  "matched_agenda_id": 40,           // 현재 매칭된 안건 (time_segments 기준)
  "suggested_agenda_id": null,       // LLM 제안 안건 (불일치 시)
  "suggestion_confidence": null,     // 제안 신뢰도 (0.0-1.0)
  "suggestion_accepted": null        // 사용자 승인 여부 (true/false/null)
}
```

### 2.2 새 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `matched_agenda_id` | int | time_segments 기준 매칭된 안건 ID |
| `suggested_agenda_id` | int \| null | LLM이 제안하는 안건 ID (불일치 시) |
| `suggestion_confidence` | float \| null | 제안 신뢰도 (0.7 이상만 표시) |
| `suggestion_accepted` | bool \| null | 사용자 승인 상태 |

---

## 3. API 설계

### 3.1 세그먼트 재매칭 분석 API

```
POST /api/v1/meetings/{meeting_id}/analyze-segments
```

**Request:**
```json
{
  "force_reanalyze": false  // true면 이미 분석된 것도 재분석
}
```

**Response:**
```json
{
  "total_segments": 39,
  "analyzed": 39,
  "mismatches_found": 3,
  "suggestions": [
    {
      "segment_index": 12,
      "segment_text": "1억 원 장학금 이벤트에 대해서...",
      "current_agenda_id": 40,
      "current_agenda_title": "대치 종로 X 맥스체대입시",
      "suggested_agenda_id": 47,
      "suggested_agenda_title": "1억 원 장학금 이벤트",
      "confidence": 0.92
    }
  ]
}
```

### 3.2 세그먼트 이동 승인 API

```
PATCH /api/v1/meetings/{meeting_id}/segments/{segment_index}/move
```

**Request:**
```json
{
  "target_agenda_id": 47,
  "accept_suggestion": true  // false면 제안 거절
}
```

**Response:**
```json
{
  "success": true,
  "segment_index": 12,
  "moved_to_agenda_id": 47,
  "time_segments_updated": true
}
```

### 3.3 일괄 승인 API

```
POST /api/v1/meetings/{meeting_id}/segments/bulk-move
```

**Request:**
```json
{
  "actions": [
    { "segment_index": 12, "accept": true },
    { "segment_index": 15, "accept": false },
    { "segment_index": 22, "accept": true, "override_agenda_id": 50 }
  ]
}
```

---

## 4. LLM 프롬프트 설계

### 4.1 분석 프롬프트

```
당신은 회의록 분석 전문가입니다.

## 안건 목록
{agendas_json}

## 대화 세그먼트
- 시간: {start}초 ~ {end}초
- 현재 매칭된 안건: {current_agenda_title}
- 대화 내용: {text}

## 작업
이 대화 내용이 현재 매칭된 안건과 관련이 있는지 판단하세요.

## 응답 형식 (JSON)
{
  "is_matched_correctly": true/false,
  "suggested_agenda_id": <안건ID 또는 null>,
  "confidence": <0.0-1.0>,
  "reason": "<판단 근거>"
}

## 규칙
- 대화 내용이 안건 제목/설명과 직접적으로 관련있어야 함
- 짧은 대화(10자 미만)는 판단 보류 (is_matched_correctly: true)
- 여러 안건에 해당할 수 있으면 가장 관련성 높은 것 선택
- confidence 0.7 미만이면 suggested_agenda_id를 null로
```

### 4.2 배치 분석 (토큰 최적화)

여러 세그먼트를 한번에 분석하여 API 호출 최소화:

```
## 대화 세그먼트 목록
[
  {"index": 0, "text": "...", "current_agenda_id": 40},
  {"index": 1, "text": "...", "current_agenda_id": 40},
  ...
]

## 응답 형식
[
  {"index": 0, "is_matched_correctly": true, ...},
  {"index": 1, "is_matched_correctly": false, "suggested_agenda_id": 47, ...},
  ...
]
```

---

## 5. 프론트엔드 설계

### 5.1 UI 컴포넌트

**대화내용 탭 (TranscriptViewer.svelte):**

```svelte
{#each segments as segment}
  <div class="segment {segment.suggested_agenda_id ? 'has-suggestion' : ''}">
    <span class="time">{formatTime(segment.start)}</span>
    <span class="text">{segment.text}</span>

    {#if segment.suggested_agenda_id && segment.suggestion_accepted === null}
      <div class="suggestion-badge">
        <span class="icon">💡</span>
        <span>이 대화는 [{suggestedAgendaTitle}]에 해당하는 것 같습니다</span>
        <button onclick={() => acceptSuggestion(segment)}>이동</button>
        <button onclick={() => rejectSuggestion(segment)}>유지</button>
      </div>
    {/if}
  </div>
{/each}
```

### 5.2 상태 표시

| 상태 | 아이콘 | 설명 |
|------|--------|------|
| 정상 매칭 | (없음) | 분석 결과 일치 |
| 제안 있음 | 💡 | LLM 제안 대기중 |
| 제안 승인 | ✅ | 사용자가 이동 승인 |
| 제안 거절 | ❌ | 사용자가 유지 선택 |

### 5.3 분석 트리거

1. **자동**: 회의록 생성 완료 후 자동 분석
2. **수동**: 결과 페이지에서 "재분석" 버튼

---

## 6. 구현 순서

### Phase 1: 백엔드 (우선순위 높음)

1. [ ] `segments` JSONB 스키마 확장 (마이그레이션 불필요 - JSONB 유연)
2. [ ] LLM 분석 서비스 (`app/services/segment_analyzer.py`)
3. [ ] 분석 API 엔드포인트 (`POST /analyze-segments`)
4. [ ] 이동 API 엔드포인트 (`PATCH /segments/{index}/move`)
5. [ ] 회의록 생성 후 자동 분석 연동

### Phase 2: 프론트엔드

1. [ ] TranscriptViewer에 제안 UI 추가
2. [ ] 승인/거절 버튼 및 API 연동
3. [ ] 재분석 버튼 추가
4. [ ] 일괄 승인 UI (선택사항)

### Phase 3: 최적화

1. [ ] 배치 분석으로 LLM 호출 최소화
2. [ ] 신뢰도 임계값 조정 (0.7 → 실험 후 결정)
3. [ ] 캐싱 전략

---

## 7. 고려사항

### 7.1 비용

| 항목 | 예상 |
|------|------|
| 세그먼트당 토큰 | ~500 tokens (input + output) |
| 39개 세그먼트 | ~20,000 tokens |
| Gemini Flash 비용 | ~$0.002 per meeting |

### 7.2 에러 처리

- LLM 응답 파싱 실패 → 해당 세그먼트 스킵, 로그 기록
- confidence < 0.7 → 제안하지 않음
- 안건 ID 유효성 검사 필수

### 7.3 UX 고려

- 너무 많은 제안 (>30%) → 경고 메시지 + 임계값 조정 제안
- 짧은 세그먼트 (단어 1-2개) → 분석 제외
- "끝", "다시" 등 메타 발화 → 분석 제외

---

## 8. 테스트 시나리오

1. **정상 케이스**: 대화 내용이 안건과 일치 → 제안 없음
2. **불일치 케이스**: 대화 내용이 다른 안건 언급 → 제안 표시
3. **짧은 대화**: 10자 미만 → 분석 스킵
4. **메타 발화**: "끝", "다시" → 분석 스킵
5. **낮은 신뢰도**: confidence < 0.7 → 제안 안함
6. **사용자 승인**: 이동 후 time_segments 업데이트 확인
7. **사용자 거절**: 제안 숨김, 상태 유지

---

## 9. 관련 파일

### 백엔드
- `app/services/segment_analyzer.py` (신규)
- `app/routers/meetings.py` (API 추가)
- `app/schemas/transcript.py` (스키마 확장)

### 프론트엔드
- `src/lib/components/results/TranscriptViewer.svelte` (UI 수정)
- `src/lib/stores/results.ts` (상태 관리)
- `src/lib/api/meetings.ts` (API 호출)
