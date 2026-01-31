# Zero Script QA - Detailed Issues & Solutions
**Document:** Issue Tracking for Max-Meeting v1.3.0
**Generated:** 2026-01-31
**Total Issues:** 17 (3 Critical, 2 High, 4 Medium, 8 Low)

---

## CRITICAL ISSUES

### ISSUE-004: No STT Pipeline Logging
**Severity:** CRITICAL | **Priority:** P1 | **Component:** Recording Workflow
**Affected File:** `/backend/app/services/stt.py`

#### Problem
The Speech-to-Text (STT) pipeline uses faster-whisper and pyannote for transcription but does NOT log processing steps. This means:
- Cannot diagnose why transcriptions fail
- Cannot measure performance (duration, quality)
- Cannot correlate transcriptions to original requests
- Worker logs provide no visibility into STT progress

#### Current State
```python
# /backend/app/services/stt.py (line ~150)
def transcribe(self, file_path: str) -> TranscriptResult:
    # No logging here
    segments, info = STTService._model.transcribe(file_path)
    speaker_segments = self.diarize_audio(file_path)
    # Processing happens with NO visibility
    return TranscriptResult(...)
```

#### Solution
```python
# Add structured logging at each step
import logging
import time
from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar('request_id', default='unknown')

logger = logging.getLogger(__name__)

class STTService:
    def transcribe(self, file_path: str, request_id: str = None) -> TranscriptResult:
        request_id = request_id or request_id_context.get()
        logger.info(
            "STT Processing started",
            extra={
                'request_id': request_id,
                'data': {'file_path': file_path}
            }
        )

        start_time = time.time()

        # Step 1: Transcription
        step_start = time.time()
        logger.info("Transcription step starting", extra={'request_id': request_id})
        segments, info = STTService._model.transcribe(file_path)
        duration_ms = (time.time() - step_start) * 1000
        logger.info(
            "Transcription complete",
            extra={
                'request_id': request_id,
                'data': {
                    'segments': len(segments),
                    'language': info.get('language'),
                    'duration_ms': round(duration_ms, 2)
                }
            }
        )

        # Step 2: Diarization
        step_start = time.time()
        logger.info("Diarization step starting", extra={'request_id': request_id})
        speaker_segments = self.diarize_audio(file_path)
        duration_ms = (time.time() - step_start) * 1000
        logger.info(
            "Diarization complete",
            extra={
                'request_id': request_id,
                'data': {
                    'speakers': len(speaker_segments),
                    'duration_ms': round(duration_ms, 2)
                }
            }
        )

        # Step 3: Merge
        total_duration = (time.time() - start_time) * 1000
        logger.info(
            "STT Processing complete",
            extra={
                'request_id': request_id,
                'data': {
                    'total_duration_ms': round(total_duration, 2),
                    'segments_count': len(segments)
                }
            }
        )

        return TranscriptResult(...)
```

#### Testing
```bash
# 1. Upload a recording and check logs
journalctl -u maxmeeting-worker -f | grep "request_id"

# 2. Verify each step is logged with timing
grep "STT Processing started" /var/log/maxmeeting-worker.log
grep "Transcription complete" /var/log/maxmeeting-worker.log
grep "Diarization complete" /var/log/maxmeeting-worker.log

# 3. Check total duration makes sense
# Expected: Whisper 5-30s, Diarization 10-60s depending on file length
```

#### Acceptance Criteria
- [ ] Every STT step logged with request_id
- [ ] Each step includes duration_ms
- [ ] Errors include stack trace with request_id
- [ ] Worker logs show processing flow
- [ ] Can correlate logs to original API call

---

### ISSUE-010: No LLM API Tracing
**Severity:** CRITICAL | **Priority:** P1 | **Component:** Result Generation
**Affected File:** `/backend/app/services/llm.py`, `/backend/app/services/gemini.py`

#### Problem
The LLM service calls Gemini API but provides NO visibility into:
- API request/response details
- Token usage (cost tracking)
- Processing duration
- Error details and retries
- Request-to-response correlation

This makes it impossible to:
- Debug result generation failures
- Track API quota usage
- Optimize prompts
- Correlate errors to requests

#### Current State
```python
# /backend/app/services/llm.py (estimated)
def generate_summary(self, meeting_id: int) -> Result:
    # No logging
    response = self.gemini_client.generate_content(prompt)
    # No visibility into what happened
    return Result(...)
```

#### Solution
```python
# Wrap Gemini client with structured logging
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

class LLMService:
    def generate_summary(
        self,
        meeting_id: int,
        prompt: str,
        request_id: str = "unknown"
    ) -> Result:
        """Generate summary using Gemini with full logging."""

        logger.info(
            "LLM Summary generation started",
            extra={
                'request_id': request_id,
                'data': {
                    'meeting_id': meeting_id,
                    'prompt_length': len(prompt)
                }
            }
        )

        start_time = time.time()

        try:
            # Call Gemini API
            response = self.gemini_client.generate_content(prompt)

            duration_ms = (time.time() - start_time) * 1000

            # Extract metrics
            usage = response.usage_metadata if hasattr(response, 'usage_metadata') else {}
            input_tokens = usage.get('prompt_token_count', 0)
            output_tokens = usage.get('candidates_token_count', 0)
            total_tokens = input_tokens + output_tokens

            logger.info(
                "LLM Summary generated",
                extra={
                    'request_id': request_id,
                    'data': {
                        'meeting_id': meeting_id,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'total_tokens': total_tokens,
                        'duration_ms': round(duration_ms, 2),
                        'output_length': len(response.text)
                    }
                }
            )

            return Result(
                content=response.text,
                tokens_used=total_tokens
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                "LLM Summary generation failed",
                extra={
                    'request_id': request_id,
                    'data': {
                        'meeting_id': meeting_id,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'duration_ms': round(duration_ms, 2)
                    }
                },
                exc_info=True
            )

            # Implement retry logic
            if self._is_retryable_error(e):
                logger.info(
                    "LLM Request will be retried",
                    extra={
                        'request_id': request_id,
                        'data': {'error': str(e)}
                    }
                )

            raise

    @staticmethod
    def _is_retryable_error(error: Exception) -> bool:
        """Check if error is retryable (quota, timeout, etc)."""
        retryable_errors = (
            'RESOURCE_EXHAUSTED',
            'DEADLINE_EXCEEDED',
            'SERVICE_UNAVAILABLE',
            'INTERNAL_ERROR'
        )
        return any(err in str(error) for err in retryable_errors)
```

#### Testing
```bash
# 1. Generate result and check logs
curl -X POST http://localhost:8000/api/v1/results \
  -H "Authorization: Bearer token" \
  -H "X-Request-ID: req_test123" \
  -d '{"meeting_id": 1}'

# 2. Check logs for LLM metrics
journalctl -u maxmeeting-api -f | grep "LLM Summary"

# 3. Verify token usage is tracked
grep "output_tokens" /var/log/maxmeeting-api.log

# 4. Test quota exhaustion error
# (Can simulate by reducing API key quota)
grep "RESOURCE_EXHAUSTED" /var/log/maxmeeting-api.log
```

#### Acceptance Criteria
- [ ] LLM API calls logged with request_id
- [ ] Token usage tracked (input, output, total)
- [ ] Processing duration logged
- [ ] Errors include retry info
- [ ] Can calculate total API costs from logs

---

### ISSUE-009: No Transcript-to-Agenda Matching
**Severity:** CRITICAL | **Priority:** P2 | **Component:** Result Generation
**Affected File:** `/backend/app/services/result.py`

#### Problem
When generating results, the system collects:
- Transcribed text segments (with timestamps)
- Agenda items (with start times from recording)

But there is NO automatic matching algorithm to connect them. This means:
- Results must be manually edited to assign transcript segments to agendas
- Users don't see which parts of recording relate to which agenda items
- Automatic action item extraction loses context
- Report generation is incomplete

#### Current State
```python
# /backend/app/services/result.py
def generate_result(self, meeting_id: int) -> Result:
    meeting = get_meeting_with_details(meeting_id)
    transcription = get_transcription(meeting_id)

    # No matching happens here
    # User must manually map segments to agendas in UI

    result = generate_from_llm(
        transcription=transcription.full_text,  # Entire text, no agenda context
        agendas=meeting.agendas,
        notes=meeting.notes
    )
    return result
```

#### Solution: Matching Algorithm
```python
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class SegmentMatch:
    """Result of matching a transcript segment to an agenda."""
    agenda_id: int
    segment_start: float
    segment_end: float
    confidence: float  # 0.0 to 1.0
    reason: str  # Why this match was chosen

class TranscriptMatcher:
    """Match transcript segments to agenda items by timestamp."""

    def match_segments_to_agendas(
        self,
        transcription: TranscriptResult,
        agendas: list[Agenda],
        request_id: str = "unknown"
    ) -> dict[int, list[SegmentMatch]]:
        """
        Match transcript segments to agenda items.

        Returns:
            dict mapping agenda_id -> list of matching segments
        """
        logger.info(
            "Agenda matching started",
            extra={
                'request_id': request_id,
                'data': {
                    'segments': len(transcription.segments),
                    'agendas': len([a for a in agendas if a.parent_id is None]),
                    'total_agendas': len(agendas)
                }
            }
        )

        matches: dict[int, list[SegmentMatch]] = {}

        # Build agenda timeline
        agenda_timeline = self._build_agenda_timeline(agendas)

        # Match each segment to nearest agenda
        for segment in transcription.segments:
            matched_agenda = self._find_matching_agenda(
                segment.start,
                segment.end,
                agenda_timeline,
                request_id
            )

            if matched_agenda:
                confidence = self._calculate_confidence(segment, matched_agenda)

                if matched_agenda['id'] not in matches:
                    matches[matched_agenda['id']] = []

                matches[matched_agenda['id']].append(SegmentMatch(
                    agenda_id=matched_agenda['id'],
                    segment_start=segment.start,
                    segment_end=segment.end,
                    confidence=confidence,
                    reason=matched_agenda['reason']
                ))

                logger.debug(
                    "Segment matched",
                    extra={
                        'request_id': request_id,
                        'data': {
                            'segment_start': segment.start,
                            'segment_end': segment.end,
                            'agenda_id': matched_agenda['id'],
                            'confidence': round(confidence, 2)
                        }
                    }
                )

        logger.info(
            "Agenda matching complete",
            extra={
                'request_id': request_id,
                'data': {
                    'matched_agendas': len(matches),
                    'total_matches': sum(len(v) for v in matches.values())
                }
            }
        )

        return matches

    def _build_agenda_timeline(self, agendas: list[Agenda]) -> list[dict]:
        """Build timeline of agenda items with start/end times."""
        timeline = []

        for agenda in agendas:
            if agenda.started_at_seconds is None:
                continue

            # Find when this agenda ends (start of next agenda or end of recording)
            end_time = None
            if hasattr(agenda, 'children') and agenda.children:
                # Children start after parent
                end_time = min(
                    c.started_at_seconds for c in agenda.children
                    if c.started_at_seconds is not None
                ) if any(c.started_at_seconds for c in agenda.children) else None

            timeline.append({
                'id': agenda.id,
                'parent_id': agenda.parent_id,
                'title': agenda.title,
                'start': agenda.started_at_seconds,
                'end': end_time,
                'level': agenda.level
            })

        return sorted(timeline, key=lambda x: x['start'])

    def _find_matching_agenda(
        self,
        segment_start: float,
        segment_end: float,
        timeline: list[dict],
        request_id: str
    ) -> Optional[dict]:
        """Find the best matching agenda for a segment."""

        # Find agendas that overlap with segment
        overlapping = []
        for agenda in timeline:
            if self._segments_overlap(
                segment_start, segment_end,
                agenda['start'], agenda['end']
            ):
                overlap_duration = self._calculate_overlap(
                    segment_start, segment_end,
                    agenda['start'], agenda['end']
                )
                overlapping.append({
                    **agenda,
                    'overlap': overlap_duration,
                    'reason': f"Timestamp overlap {round(overlap_duration, 1)}s"
                })

        # Return agenda with maximum overlap
        if overlapping:
            return max(overlapping, key=lambda x: x['overlap'])

        # Fallback: find nearest agenda
        nearest = min(
            timeline,
            key=lambda a: abs(segment_start - a['start']),
            default=None
        )

        if nearest:
            distance = abs(segment_start - nearest['start'])
            nearest['reason'] = f"Nearest agenda {distance}s away"
            return nearest

        return None

    @staticmethod
    def _segments_overlap(
        seg1_start: float,
        seg1_end: float,
        seg2_start: Optional[float],
        seg2_end: Optional[float]
    ) -> bool:
        """Check if two time segments overlap."""
        if seg2_start is None:
            return False
        if seg2_end is None:
            return seg1_start < seg2_end and seg1_end > seg2_start
        return seg1_start < seg2_end and seg1_end > seg2_start

    @staticmethod
    def _calculate_overlap(
        seg1_start: float,
        seg1_end: float,
        seg2_start: Optional[float],
        seg2_end: Optional[float]
    ) -> float:
        """Calculate overlap duration between two segments."""
        if seg2_start is None:
            return 0
        overlap_start = max(seg1_start, seg2_start)
        overlap_end = min(seg1_end, seg2_end or seg1_end)
        return max(0, overlap_end - overlap_start)

    @staticmethod
    def _calculate_confidence(
        segment: TranscriptSegment,
        agenda: dict
    ) -> float:
        """Calculate matching confidence (0.0 to 1.0)."""
        # Start with segment confidence from STT
        confidence = segment.confidence

        # Adjust based on overlap quality
        if agenda['reason'].startswith('Timestamp'):
            confidence *= 0.95  # Good match
        else:
            confidence *= 0.5   # Fallback match

        return min(1.0, confidence)

# Usage in result service
def generate_result_with_matching(self, meeting_id: int, request_id: str):
    meeting = self.get_meeting_with_details(meeting_id)
    transcription = self.get_transcription(meeting_id)

    # Match segments to agendas
    matcher = TranscriptMatcher()
    matches = matcher.match_segments_to_agendas(
        transcription=transcription,
        agendas=meeting.agendas,
        request_id=request_id
    )

    # Build context-aware prompt for LLM
    prompt = self._build_prompt_with_context(
        transcription=transcription,
        matches=matches,
        agendas=meeting.agendas,
        notes=meeting.notes
    )

    # Generate result with full context
    result = self.llm_service.generate_summary(
        prompt=prompt,
        request_id=request_id
    )

    return result
```

#### Testing
```bash
# 1. Create a meeting with clear agenda items
# 2. Record with clear agenda switching (announce each topic)
# 3. Upload recording
# 4. Check logs for matching
journalctl -u maxmeeting-worker -f | grep "Agenda matching"

# 5. Verify confidence scores
grep "confidence" /var/log/maxmeeting-worker.log

# 6. Generate result and check if segments are correctly attributed
curl http://localhost:8000/api/v1/meetings/1/results

# 7. Inspect result.segments field to verify matching worked
```

#### Acceptance Criteria
- [ ] Segments automatically matched to agenda items
- [ ] Matching algorithm respects timestamps
- [ ] Confidence scores calculated and logged
- [ ] Fallback matching for unmatched segments
- [ ] Result includes agenda context in generated summary

---

## HIGH PRIORITY ISSUES

### ISSUE-001: No API Request Logging
**Severity:** WARNING | **Priority:** P1 | **Component:** Backend API
**Affected File:** `/backend/app/main.py`

#### Problem
- API endpoints return responses but don't log request/response details
- Cannot see response times (duration_ms)
- Cannot see error details in logs
- Audit trail only in database, not in console logs

#### Solution
Create middleware in `/backend/app/middleware/logging.py`:
```python
import json
import logging
import time
from typing import Callable
from fastapi import Request, Response

logger = logging.getLogger(__name__)

class JSONLogFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": "api",
            "request_id": getattr(record, 'request_id', 'N/A'),
            "message": record.getMessage(),
        }
        if hasattr(record, 'data'):
            log_data["data"] = record.data
        return json.dumps(log_data)

async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """Log all API requests and responses with timing."""
    request_id = getattr(request.state, 'request_id', 'unknown')

    start_time = time.time()

    # Log request
    logger.info(
        f"{request.method} {request.url.path}",
        extra={
            'request_id': request_id,
            'data': {
                'method': request.method,
                'path': request.url.path,
                'query_params': dict(request.query_params),
                'client_ip': request.client.host if request.client else None
            }
        }
    )

    # Get response
    response = await call_next(request)

    # Log response
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code}",
        extra={
            'request_id': request_id,
            'data': {
                'method': request.method,
                'path': request.url.path,
                'status': response.status_code,
                'duration_ms': round(duration_ms, 2)
            }
        }
    )

    return response
```

Then register in `main.py`:
```python
from app.middleware.logging import logging_middleware

app.middleware("http")(logging_middleware)
```

#### Testing
```bash
# 1. Make API request
curl http://localhost:8000/api/v1/meetings/1

# 2. Check logs show request and response
journalctl -u maxmeeting-api -f | grep "POST /api/v1/meetings"

# 3. Verify duration_ms is present
grep "duration_ms" /var/log/maxmeeting-api.log
```

#### Acceptance Criteria
- [ ] All API requests logged with duration_ms
- [ ] Responses logged with status code
- [ ] Request-ID included in logs
- [ ] Can correlate requests to responses
- [ ] Performance metrics visible in logs

---

### ISSUE-005: No Upload Progress Tracking
**Severity:** CRITICAL | **Priority:** P1 | **Component:** Recording Workflow
**Affected File:** `/backend/app/routers/recordings.py`

#### Problem
- Recording upload can take several minutes
- No logging of upload progress (chunk 1/10, 2/10, etc.)
- No visibility into whether upload is working or stuck
- No duration_ms tracking for upload completion

#### Solution
Add logging to upload handler:
```python
@router.post("/recordings/{recording_id}/upload")
async def upload_chunk(
    recording_id: int,
    chunk_index: int,
    chunk_data: bytes,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, 'request_id', 'unknown')
    start_time = time.time()

    logger.info(
        "Recording upload chunk started",
        extra={
            'request_id': request_id,
            'data': {
                'recording_id': recording_id,
                'chunk_index': chunk_index,
                'chunk_size': len(chunk_data)
            }
        }
    )

    try:
        # Save chunk
        recording = await recording_service.update_chunk(
            recording_id, chunk_index, chunk_data
        )

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Recording upload chunk complete",
            extra={
                'request_id': request_id,
                'data': {
                    'recording_id': recording_id,
                    'chunk_index': chunk_index,
                    'duration_ms': round(duration_ms, 2),
                    'progress_percent': int((chunk_index / recording.total_chunks) * 100)
                }
            }
        )

        return {'status': 'chunk_saved'}

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        logger.error(
            "Recording upload chunk failed",
            extra={
                'request_id': request_id,
                'data': {
                    'recording_id': recording_id,
                    'chunk_index': chunk_index,
                    'error': str(e),
                    'duration_ms': round(duration_ms, 2)
                }
            },
            exc_info=True
        )
        raise
```

#### Testing
```bash
# 1. Upload a recording
# 2. Check logs during upload
journalctl -u maxmeeting-api -f | grep "Recording upload"

# 3. Verify progress shown
grep "progress_percent" /var/log/maxmeeting-api.log

# 4. Check total upload time
grep "chunk complete" /var/log/maxmeeting-api.log | tail -1
```

---

## MEDIUM PRIORITY ISSUES

### ISSUE-006: Lost Request Context in STT Service
**Severity:** WARNING | **Priority:** P2 | **Component:** Recording Workflow

Pass request_id through service layer:
```python
# Before
result = await stt_service.transcribe(file_path)

# After
result = await stt_service.transcribe(file_path, request_id=request_id)
```

### ISSUE-007: Missing Timestamp Validation
**Severity:** WARNING | **Priority:** P2 | **Component:** Recording Workflow

Add validation:
```python
if agenda.started_at_seconds is None:
    logger.warning(
        "Agenda missing timestamp",
        extra={
            'request_id': request_id,
            'data': {'agenda_id': agenda.id}
        }
    )
```

### ISSUE-014: Frontend Error Tracing
**Severity:** WARNING | **Priority:** P2 | **Component:** Frontend
**Affected File:** `/frontend/src/lib/api.ts`

Generate request_id and include in all errors:
```typescript
private async fetchWithAuth<T>(
    url: string,
    options: RequestInit
): Promise<T> {
    const request_id = generateRequestId();
    const headers = {
        ...(options.headers || {}),
        'X-Request-ID': request_id
    };

    // Include request_id in error context
    try {
        const response = await fetch(url, { ...options, headers });
        // ...
    } catch (error) {
        logger.error('API call failed', {
            request_id,
            error: error.message,
            endpoint: url
        });
        throw error;
    }
}
```

---

## LOW PRIORITY ISSUES

### ISSUE-002, ISSUE-003, ISSUE-008, ISSUE-011, ISSUE-012, ISSUE-013, ISSUE-015, ISSUE-016, ISSUE-017

These are all INFO or nice-to-have improvements. See main QA report for details.

All require consistent structured logging implementation across backend and frontend.

---

## Implementation Checklist

### Before Production Deploy
- [ ] ISSUE-004: STT Pipeline Logging
- [ ] ISSUE-010: LLM API Tracing
- [ ] ISSUE-001: Backend JSON Logging Middleware (if time permits)

### v1.3.1 (Within 1 week)
- [ ] ISSUE-005: Upload Progress Tracking
- [ ] ISSUE-014: Frontend Request ID generation
- [ ] ISSUE-006: Request context propagation

### v1.4.0 (Within 1 month)
- [ ] ISSUE-009: Transcript-to-Agenda Matching
- [ ] ISSUE-007: Timestamp Validation
- [ ] ISSUE-011: Result generation timeout
- [ ] All remaining INFO-level issues

---

Generated by Zero Script QA
Date: 2026-01-31
