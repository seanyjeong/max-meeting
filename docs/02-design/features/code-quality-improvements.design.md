# Code Quality Improvements Design

> MAX Meeting 코드 품질 개선 상세 설계

## 메타 정보

| 항목 | 값 |
|------|-----|
| **Feature** | code-quality-improvements |
| **Version** | v1.6.0 |
| **Created** | 2026-01-30 |
| **Plan** | [code-quality-improvements.plan.md](../../01-plan/features/code-quality-improvements.plan.md) |
| **Status** | Draft |

---

## 1. Phase 1: Critical 보안 이슈

### 1.1 SQL Injection 수정

**파일**: `backend/app/services/contact.py:48`

**현재 코드**:
```python
search_filter = Contact.name.ilike(f"%{q}%")
```

**문제점**: 사용자 입력 `q`가 직접 LIKE 패턴에 삽입되어 `%`, `_` 특수문자로 의도치 않은 검색 가능

**수정 코드**:
```python
def escape_like(value: str) -> str:
    """LIKE 패턴 특수문자 이스케이프"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

# 사용
if q:
    escaped_q = escape_like(q)
    search_filter = Contact.name.ilike(f"%{escaped_q}%", escape="\\")
    base_query = base_query.where(search_filter)
```

**테스트**:
```bash
# 특수문자 검색 테스트
curl -X GET "http://localhost:9000/api/v1/contacts?q=%25test%25"
curl -X GET "http://localhost:9000/api/v1/contacts?q=test_name"
```

---

### 1.2 Deprecated asyncio 교체

**파일**:
- `backend/workers/tasks/stt.py:359, 442`
- `backend/workers/tasks/llm.py:442`

**현재 코드**:
```python
result = asyncio.get_event_loop().run_until_complete(_async_func())
```

**문제점**: Python 3.10+에서 deprecated, 3.12에서 DeprecationWarning 발생

**수정 코드**:
```python
# 방법 1: asyncio.run() 사용 (권장)
result = asyncio.run(_async_func())

# 방법 2: 새 이벤트 루프 생성 (Celery 환경에서 안전)
def run_async(coro):
    """Celery 워커에서 async 코드 실행"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

result = run_async(_async_func())
```

**적용 위치**:

| 파일 | 라인 | 함수 |
|------|------|------|
| stt.py | 359 | `save_transcript()` 내 `_save()` |
| stt.py | 442 | `process_recording()` 내 `_get_recording()` |
| llm.py | 442 | `generate_meeting_result()` 내 `_generate()` |

**테스트**:
```bash
# STT 워커 테스트
celery -A workers.celery_app worker --loglevel=info -Q stt

# LLM 워커 테스트
celery -A workers.celery_app worker --loglevel=info -Q llm
```

---

### 1.3 소유권 검증 추가

**파일**: `backend/app/routers/results.py:225-303`

**현재 문제**: 인증된 사용자가 다른 사용자의 회의 데이터에 접근 가능

**수정 방안**:

#### Step 1: MeetingService에 소유권 검증 메서드 추가

```python
# backend/app/services/meeting.py

async def verify_ownership(self, meeting_id: int, user_id: str) -> bool:
    """회의 소유권 검증"""
    query = select(Meeting).where(
        Meeting.id == meeting_id,
        Meeting.created_by == user_id,
        Meeting.deleted_at.is_(None)
    )
    result = await self.db.execute(query)
    return result.scalar_one_or_none() is not None

async def get_meeting_or_403(self, meeting_id: int, user_id: str) -> Meeting:
    """회의 조회 (소유권 검증 포함)"""
    if not await self.verify_ownership(meeting_id, user_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return await self.get_by_id(meeting_id)
```

#### Step 2: ResultService에 토론 조회 메서드 추가

```python
# backend/app/services/result.py

async def get_discussions(self, meeting_id: int) -> list[dict]:
    """회의 토론 목록 조회"""
    # 기존 routers/results.py:232-303 로직 이동
    ...
```

#### Step 3: 라우터 수정

```python
# backend/app/routers/results.py

@router.get("/meetings/{meeting_id}/discussions")
async def get_meeting_discussions(
    meeting_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    # 소유권 검증
    meeting_service = MeetingService(db)
    await meeting_service.get_meeting_or_403(meeting_id, current_user["user_id"])

    # 서비스 호출
    result_service = ResultService(db)
    discussions = await result_service.get_discussions(meeting_id)
    return {"data": discussions}
```

---

### 1.4 프로덕션 로그 정리

**파일**: `frontend/src/lib/api.ts:121, 131`

**현재 코드**:
```typescript
console.error('[API] Error response:', errorData);
console.log('[API] Response data:', JSON.stringify(jsonData).slice(0, 200));
```

**수정 코드**:
```typescript
// frontend/src/lib/utils/logger.ts (신규)
const isDev = import.meta.env.DEV;

export const logger = {
    debug: (...args: unknown[]) => isDev && console.log(...args),
    info: (...args: unknown[]) => isDev && console.info(...args),
    warn: (...args: unknown[]) => console.warn(...args),  // 항상 출력
    error: (...args: unknown[]) => console.error(...args), // 항상 출력
};

// frontend/src/lib/api.ts
import { logger } from './utils/logger';

// 변경
logger.error('[API] Error response:', errorData);
logger.debug('[API] Response data:', JSON.stringify(jsonData).slice(0, 200));
```

---

### 1.5 토큰 저장 방식 문서화

**파일**: `frontend/src/lib/stores/auth.ts`

**현재 방식**: localStorage에 accessToken, refreshToken 저장

**위험성**:
- XSS 공격 시 JavaScript로 토큰 탈취 가능
- 서드파티 스크립트에서 접근 가능

**결정**: 현재 방식 유지 + 문서화 (단일 사용자 시스템이므로)

**문서화 추가**:
```typescript
/**
 * Auth Store - Authentication state management
 *
 * ⚠️ SECURITY NOTE:
 * Tokens are stored in localStorage for simplicity.
 * This is acceptable for this single-user internal system.
 *
 * For multi-user production systems, consider:
 * - httpOnly cookies (prevents XSS token theft)
 * - Memory storage + refresh on page load
 * - Short-lived access tokens (current: 60min)
 *
 * Current mitigations:
 * - CSP headers prevent inline scripts
 * - No third-party scripts loaded
 * - Token expiry: 60 minutes
 */
```

---

## 2. Phase 2: 코드 품질 개선

### 2.1 유틸리티 함수 통합

**신규 파일**: `frontend/src/lib/utils/format.ts`

```typescript
/**
 * Date/Time formatting utilities
 */

export function formatDate(dateString: string | Date): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

export function formatDateTime(dateString: string | Date): string {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

export function formatTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

export function formatDuration(ms: number): string {
    const seconds = Math.floor(ms / 1000);
    return formatTime(seconds);
}

export function truncate(str: string, maxLength: number): string {
    if (str.length <= maxLength) return str;
    return str.slice(0, maxLength - 3) + '...';
}
```

**변경 대상 파일** (9개):
| 파일 | 변경 내용 |
|------|----------|
| `routes/+page.svelte` | formatDate 제거, import 추가 |
| `routes/meetings/[id]/+page.svelte` | formatDate 제거, import 추가 |
| `routes/meetings/[id]/results/+page.svelte` | formatDate 제거, import 추가 |
| `routes/meetings/[id]/results/report/+page.svelte` | formatDate 제거, import 추가 |
| `routes/meetings/deleted/+page.svelte` | formatDate 제거, import 추가 |
| `components/results/ActionItems.svelte` | formatDate 제거, import 추가 |
| `components/results/RecordingsList.svelte` | formatDate 제거, import 추가 |
| `components/ui/MeetingCard.svelte` | formatDate 제거, import 추가 |
| `components/SyncConflictDialog.svelte` | formatDate 제거, import 추가 |

---

### 2.2 results/+page.svelte 분할

**현재**: 1063줄 단일 파일

**분할 계획**:

```
frontend/src/lib/components/results/
├── ResultsHeader.svelte       # 헤더 + 회의 정보 (약 100줄)
├── ResultsStatus.svelte       # STT/LLM 상태 표시 (약 150줄)
├── ResultsFilter.svelte       # 안건 필터 드롭다운 (약 80줄)
├── ResultsSummary.svelte      # 요약 섹션 (약 100줄)
├── ResultsTranscript.svelte   # 대화 내용 섹션 (약 150줄)
└── ResultsActions.svelte      # 실행항목 섹션 (약 100줄)

routes/meetings/[id]/results/+page.svelte  # 조합 + 상태관리 (약 300줄)
```

**Props 인터페이스**:

```typescript
// ResultsHeader.svelte
interface Props {
    meeting: Meeting;
    onBack: () => void;
}

// ResultsStatus.svelte
interface Props {
    recordings: Recording[];
    sttStatus: ProcessingStatus;
    llmStatus: ProcessingStatus;
    currentTime: number;
    onGenerateResult: () => void;
}

// ResultsFilter.svelte
interface Props {
    agendas: Agenda[];
    selectedAgendaId: number | null;
    onSelect: (id: number | null) => void;
}
```

---

### 2.3 [id]/+page.svelte 분할

**현재**: 689줄 단일 파일

**분할 계획**:

```
frontend/src/lib/components/meeting/
├── MeetingHeader.svelte       # 헤더 + 기본 정보 (약 80줄)
├── AgendaSection.svelte       # 안건 목록 + 편집 (약 200줄)
├── QuestionSection.svelte     # 질문 목록 + 생성 (약 150줄)
├── ParticipantSection.svelte  # 참석자 관리 (약 100줄)
└── MeetingActions.svelte      # 하단 액션 버튼들 (약 60줄)

routes/meetings/[id]/+page.svelte  # 조합 + 상태관리 (약 200줄)
```

---

### 2.4 console.log 정리

**전략**:
1. `$lib/utils/logger.ts` 생성 (1.4에서 생성)
2. 모든 console.log → logger.debug 변경
3. console.error → logger.error 유지
4. 프로덕션 빌드 시 DEV 로그 제거됨

**스크립트로 일괄 변경**:
```bash
# 변경 대상 파일 검색
grep -r "console.log" frontend/src --include="*.ts" --include="*.svelte" -l

# 변경 후 빌드 테스트
cd frontend && npm run build
```

---

### 2.5 Backend 중복 코드 제거

**파일**: `backend/app/routers/agendas.py`

**중복 로직**: 질문 생성 (lines 96-121, 148-170)

**추출 함수**:
```python
# backend/app/services/agenda.py

async def generate_questions_for_agenda(
    self,
    agenda: Agenda,
    num_questions: int = 4,
    background: bool = True
) -> None:
    """안건에 대한 질문 생성 (Celery 태스크 호출)"""
    from workers.tasks.llm import generate_questions

    if background:
        generate_questions.delay(agenda.id, num_questions)
    else:
        generate_questions(agenda.id, num_questions)
```

**라우터 수정**:
```python
# create_agenda, parse_agenda_text에서 공통 함수 호출
await agenda_service.generate_questions_for_agenda(agenda)
```

---

## 3. Phase 3: 아키텍처 개선

### 3.1 프롬프트 외부화

**디렉토리 구조**:
```
backend/
├── prompts/
│   ├── meeting_summary.yaml
│   ├── agenda_parsing.yaml
│   ├── question_generation.yaml
│   └── __init__.py
├── app/
│   └── services/
│       └── prompt_loader.py
```

**YAML 형식**:
```yaml
# prompts/meeting_summary.yaml
name: meeting_summary
version: "1.0"
description: "회의록 요약 생성 프롬프트"

system: |
  You are a professional meeting minutes writer.
  ...

user_template: |
  # Meeting Information
  Title: {title}
  Date: {date}

  # Agenda
  {agenda_list}

  # Transcript
  {transcript}

parameters:
  max_tokens: 4000
  temperature: 0.3
```

**로더 구현**:
```python
# backend/app/services/prompt_loader.py
import yaml
from pathlib import Path
from functools import lru_cache

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

@lru_cache(maxsize=10)
def load_prompt(name: str) -> dict:
    """YAML 프롬프트 로드 (캐싱)"""
    path = PROMPTS_DIR / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def render_prompt(name: str, **kwargs) -> str:
    """프롬프트 렌더링"""
    prompt = load_prompt(name)
    return prompt["user_template"].format(**kwargs)
```

---

### 3.2 대형 함수 분할

**stt.py `process_recording()` 분할**:

```python
# 현재: 150줄+ 단일 함수

# 분할 후:
def process_recording(self, recording_id: int, language: str = "ko"):
    """메인 오케스트레이션 함수"""
    recording_info = self._get_recording_info(recording_id)
    chunks = self._split_audio(recording_info["file_path"])
    segments = self._transcribe_chunks(chunks, language)
    result = self._merge_results(segments)
    transcript_id = self._save_transcript(recording_id, result)
    return {"recording_id": recording_id, "transcript_id": transcript_id}

def _get_recording_info(self, recording_id: int) -> dict:
    """DB에서 녹음 정보 조회"""
    ...

def _split_audio(self, file_path: str) -> list[str]:
    """오디오 파일 청크 분할"""
    ...

def _transcribe_chunks(self, chunks: list[str], language: str) -> list[dict]:
    """청크별 STT 처리"""
    ...

def _merge_results(self, segments: list[dict]) -> dict:
    """결과 병합"""
    ...

def _save_transcript(self, recording_id: int, result: dict) -> int:
    """DB 저장"""
    ...
```

---

### 3.3 에러 처리 통합

**신규 파일**: `frontend/src/lib/utils/error.ts`

```typescript
/**
 * Centralized error handling utilities
 */
import { toast } from '$lib/stores/toast';

interface ApiErrorData {
    code?: string;
    message?: string;
    status?: number;
}

export function isApiError(error: unknown): error is ApiErrorData {
    return (
        typeof error === 'object' &&
        error !== null &&
        ('code' in error || 'message' in error)
    );
}

export function handleApiError(error: unknown, context?: string): void {
    const prefix = context ? `[${context}] ` : '';

    if (isApiError(error)) {
        toast.error(`${prefix}${error.message || '알 수 없는 오류'}`);
    } else if (error instanceof Error) {
        toast.error(`${prefix}${error.message}`);
    } else {
        toast.error(`${prefix}오류가 발생했습니다`);
    }

    // 프로덕션에서도 에러는 로깅
    console.error(prefix, error);
}

export function assertNever(x: never): never {
    throw new Error(`Unexpected value: ${x}`);
}
```

**사용 예**:
```typescript
try {
    await api.meetings.delete(id);
} catch (error) {
    handleApiError(error, '회의 삭제');
}
```

---

### 3.4 타입 안전성 강화

**변경 대상**:
```typescript
// Before
} catch (error: any) {
    console.error(error.message);
}

// After
} catch (error: unknown) {
    if (error instanceof Error) {
        console.error(error.message);
    } else {
        console.error('Unknown error:', error);
    }
}
```

**타입 가드 함수**:
```typescript
// frontend/src/lib/utils/types.ts

export function isError(value: unknown): value is Error {
    return value instanceof Error;
}

export function isString(value: unknown): value is string {
    return typeof value === 'string';
}

export function isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function hasProperty<K extends string>(
    obj: unknown,
    key: K
): obj is { [P in K]: unknown } {
    return isObject(obj) && key in obj;
}
```

---

## 4. 구현 순서

```
Phase 1 (즉시, 1일)
├── 1.1 SQL Injection 수정
├── 1.2 Deprecated asyncio 교체
├── 1.3 소유권 검증 추가
├── 1.4 프로덕션 로그 정리
└── 1.5 토큰 저장 문서화

Phase 2 (단기, 2-3일)
├── 2.1 유틸리티 함수 통합
├── 2.2 results/+page.svelte 분할
├── 2.3 [id]/+page.svelte 분할
├── 2.4 console.log 정리
└── 2.5 Backend 중복 제거

Phase 3 (중기, 3-5일)
├── 3.1 프롬프트 외부화
├── 3.2 대형 함수 분할
├── 3.3 에러 처리 통합
└── 3.4 타입 안전성 강화
```

---

## 5. 검증 체크리스트

### Phase 1 완료 조건
- [ ] SQL Injection 테스트 통과 (`%`, `_` 특수문자)
- [ ] STT 워커 정상 동작
- [ ] LLM 워커 정상 동작
- [ ] 프로덕션 빌드 시 debug 로그 없음
- [ ] 다른 사용자 회의 접근 시 403 반환

### Phase 2 완료 조건
- [ ] formatDate import 누락 없음 (빌드 성공)
- [ ] 모든 페이지 정상 렌더링
- [ ] 컴포넌트 props 타입 체크 통과
- [ ] console.log → logger 변경 완료

### Phase 3 완료 조건
- [ ] 프롬프트 YAML 로딩 정상
- [ ] 함수 분할 후 동일 동작 확인
- [ ] 타입 체크 통과 (strict mode)

---

## Changelog

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-01-30 | 0.1 | 초안 작성 |
