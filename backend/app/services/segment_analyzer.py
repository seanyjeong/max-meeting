"""Segment Analyzer Service - LLM-based transcript segment analysis."""

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Meeting, Agenda, Transcript
from app.services.llm import LLMService

logger = logging.getLogger(__name__)


class SegmentSuggestion:
    """Represents a suggestion for a segment rematch."""

    def __init__(
        self,
        segment_index: int,
        segment_text: str,
        current_agenda_id: int | None,
        current_agenda_title: str | None,
        suggested_agenda_id: int | None,
        suggested_agenda_title: str | None,
        confidence: float,
        reason: str,
    ):
        self.segment_index = segment_index
        self.segment_text = segment_text
        self.current_agenda_id = current_agenda_id
        self.current_agenda_title = current_agenda_title
        self.suggested_agenda_id = suggested_agenda_id
        self.suggested_agenda_title = suggested_agenda_title
        self.confidence = confidence
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "segment_index": self.segment_index,
            "segment_text": self.segment_text[:100] + "..." if len(self.segment_text) > 100 else self.segment_text,
            "current_agenda_id": self.current_agenda_id,
            "current_agenda_title": self.current_agenda_title,
            "suggested_agenda_id": self.suggested_agenda_id,
            "suggested_agenda_title": self.suggested_agenda_title,
            "confidence": self.confidence,
            "reason": self.reason,
        }


class SegmentAnalyzer:
    """Analyzes transcript segments to detect agenda mismatches."""

    MIN_TEXT_LENGTH = 10  # Minimum text length to analyze
    MIN_CONFIDENCE = 0.7  # Minimum confidence to suggest
    SKIP_PATTERNS = ["끝", "다시", "네", "예", "아", "음"]  # Meta utterances to skip

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()

    def _find_matched_agenda(
        self,
        segment_start: float,
        agendas: list[Agenda],
    ) -> Agenda | None:
        """Find which agenda a segment belongs to based on time_segments."""
        for agenda in agendas:
            if agenda.time_segments:
                for ts in agenda.time_segments:
                    start = ts.get("start", 0)
                    end = ts.get("end")
                    if end is None:
                        end = float("inf")
                    if start <= segment_start < end:
                        return agenda
            # Fallback to started_at_seconds
            elif agenda.started_at_seconds is not None:
                # This is a simplified check; real implementation would need end time
                if segment_start >= agenda.started_at_seconds:
                    return agenda
        return None

    def _should_skip_segment(self, text: str) -> bool:
        """Check if segment should be skipped from analysis."""
        text = text.strip()
        if len(text) < self.MIN_TEXT_LENGTH:
            return True
        if text in self.SKIP_PATTERNS:
            return True
        return False

    def _build_analysis_prompt(
        self,
        agendas: list[Agenda],
        segments_batch: list[dict],
    ) -> str:
        """Build the LLM prompt for segment analysis."""
        # Build agenda list
        agenda_list = []
        for agenda in agendas:
            agenda_info = {
                "id": agenda.id,
                "title": agenda.title,
                "description": agenda.description,
                "level": agenda.level,
            }
            agenda_list.append(agenda_info)

        # Build segments list
        segments_list = []
        for seg in segments_batch:
            segments_list.append({
                "index": seg["index"],
                "text": seg["text"],
                "current_agenda_id": seg["current_agenda_id"],
                "current_agenda_title": seg["current_agenda_title"],
            })

        prompt = f"""당신은 회의록 분석 전문가입니다.

## 안건 목록
```json
{json.dumps(agenda_list, ensure_ascii=False, indent=2)}
```

## 분석할 대화 세그먼트
```json
{json.dumps(segments_list, ensure_ascii=False, indent=2)}
```

## 작업
각 대화 세그먼트가 현재 매칭된 안건과 관련이 있는지 판단하세요.

## 응답 형식 (JSON 배열)
```json
[
  {{
    "index": 0,
    "is_matched_correctly": true,
    "suggested_agenda_id": null,
    "confidence": 0.0,
    "reason": "판단 근거"
  }},
  {{
    "index": 1,
    "is_matched_correctly": false,
    "suggested_agenda_id": 47,
    "confidence": 0.85,
    "reason": "대화 내용이 '1억 원 장학금'을 직접 언급함"
  }}
]
```

## 규칙
1. 대화 내용이 안건 제목/설명과 직접적으로 관련있어야 함
2. 여러 안건에 해당할 수 있으면 가장 관련성 높은 것 선택
3. confidence 0.7 미만이면 suggested_agenda_id를 null로 설정
4. is_matched_correctly가 true면 suggested_agenda_id는 null
5. JSON 형식만 응답 (다른 텍스트 없이)"""

        return prompt

    async def analyze_segments(
        self,
        meeting: Meeting,
        force_reanalyze: bool = False,
    ) -> dict:
        """Analyze all segments in a meeting for agenda mismatches."""
        # Get all agendas (flat list)
        agendas = [a for a in meeting.agendas if a.deleted_at is None]
        agenda_map = {a.id: a for a in agendas}

        # Get transcripts
        transcripts = meeting.transcripts
        if not transcripts:
            return {
                "total_segments": 0,
                "analyzed": 0,
                "mismatches_found": 0,
                "suggestions": [],
            }

        # Collect all segments
        all_segments = []
        for transcript in transcripts:
            if transcript.segments:
                for idx, seg in enumerate(transcript.segments):
                    all_segments.append({
                        "transcript_id": transcript.id,
                        "index": idx,
                        "global_index": len(all_segments),
                        "text": seg.get("text", ""),
                        "start": seg.get("start", 0),
                        "end": seg.get("end"),
                        "raw_segment": seg,
                    })

        if not all_segments:
            return {
                "total_segments": 0,
                "analyzed": 0,
                "mismatches_found": 0,
                "suggestions": [],
            }

        # Find current agenda for each segment and filter
        segments_to_analyze = []
        for seg in all_segments:
            # Skip if already has suggestion and not force_reanalyze
            if not force_reanalyze and seg["raw_segment"].get("suggested_agenda_id") is not None:
                continue

            # Skip short/meta segments
            if self._should_skip_segment(seg["text"]):
                continue

            # Find matched agenda
            matched_agenda = self._find_matched_agenda(seg["start"], agendas)
            seg["current_agenda_id"] = matched_agenda.id if matched_agenda else None
            seg["current_agenda_title"] = matched_agenda.title if matched_agenda else None

            segments_to_analyze.append(seg)

        if not segments_to_analyze:
            return {
                "total_segments": len(all_segments),
                "analyzed": 0,
                "mismatches_found": 0,
                "suggestions": [],
            }

        # Build prompt and call LLM
        prompt = self._build_analysis_prompt(agendas, segments_to_analyze)

        try:
            response = await self.llm_service.generate_text(prompt)
            # Parse JSON response
            # Try to extract JSON from response
            response_text = response.strip()
            if response_text.startswith("```"):
                # Remove markdown code block
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])

            results = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Response was: {response[:500]}")
            return {
                "total_segments": len(all_segments),
                "analyzed": len(segments_to_analyze),
                "mismatches_found": 0,
                "suggestions": [],
                "error": "LLM 응답 파싱 실패",
            }
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {
                "total_segments": len(all_segments),
                "analyzed": 0,
                "mismatches_found": 0,
                "suggestions": [],
                "error": str(e),
            }

        # Process results
        suggestions = []
        for result in results:
            idx = result.get("index")
            if idx is None:
                continue

            seg = next((s for s in segments_to_analyze if s["global_index"] == idx), None)
            if not seg:
                continue

            is_matched = result.get("is_matched_correctly", True)
            suggested_id = result.get("suggested_agenda_id")
            confidence = result.get("confidence", 0)
            reason = result.get("reason", "")

            if not is_matched and suggested_id and confidence >= self.MIN_CONFIDENCE:
                suggested_agenda = agenda_map.get(suggested_id)
                suggestion = SegmentSuggestion(
                    segment_index=seg["global_index"],
                    segment_text=seg["text"],
                    current_agenda_id=seg["current_agenda_id"],
                    current_agenda_title=seg["current_agenda_title"],
                    suggested_agenda_id=suggested_id,
                    suggested_agenda_title=suggested_agenda.title if suggested_agenda else None,
                    confidence=confidence,
                    reason=reason,
                )
                suggestions.append(suggestion)

        return {
            "total_segments": len(all_segments),
            "analyzed": len(segments_to_analyze),
            "mismatches_found": len(suggestions),
            "suggestions": [s.to_dict() for s in suggestions],
        }

    async def move_segment(
        self,
        meeting: Meeting,
        segment_index: int,
        target_agenda_id: int,
        accept_suggestion: bool = True,
    ) -> dict:
        """Move a segment to a different agenda by updating time_segments."""
        # Find the segment
        all_segments = []
        target_transcript = None
        target_seg_idx = None

        for transcript in meeting.transcripts:
            if transcript.segments:
                for idx, seg in enumerate(transcript.segments):
                    if len(all_segments) == segment_index:
                        target_transcript = transcript
                        target_seg_idx = idx
                    all_segments.append(seg)

        if target_transcript is None or target_seg_idx is None:
            return {"success": False, "error": "Segment not found"}

        segment = target_transcript.segments[target_seg_idx]
        segment_start = segment.get("start", 0)
        segment_end = segment.get("end", segment_start + 1)

        # Find target agenda
        target_agenda = next(
            (a for a in meeting.agendas if a.id == target_agenda_id),
            None,
        )
        if not target_agenda:
            return {"success": False, "error": "Target agenda not found"}

        # Update segment metadata
        segment["matched_agenda_id"] = target_agenda_id
        segment["suggestion_accepted"] = accept_suggestion
        if accept_suggestion:
            segment["suggested_agenda_id"] = None  # Clear suggestion after accepting

        # Update target agenda's time_segments
        if target_agenda.time_segments is None:
            target_agenda.time_segments = []

        # Add new time range (simplified - might need merging logic)
        new_range = {"start": segment_start, "end": segment_end}
        target_agenda.time_segments.append(new_range)

        # Mark transcript as modified
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(target_transcript, "segments")
        flag_modified(target_agenda, "time_segments")

        await self.db.flush()

        return {
            "success": True,
            "segment_index": segment_index,
            "moved_to_agenda_id": target_agenda_id,
            "time_segments_updated": True,
        }
