"""
LLM service abstraction layer.

Provides a unified interface for LLM providers (Gemini, OpenAI).
Based on spec Section 9 (LLM Prompt Strategy).
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


# ==================== LLM Logging Helper ====================

async def log_llm_operation(
    operation: str,
    meeting_id: int | None,
    agenda_id: int | None,
    provider: str,
    model: str,
    start_time: float,
    prompt_length: int,
    response_length: int,
    prompt_tokens: int,
    completion_tokens: int,
    error: Exception | None = None,
):
    """Log LLM operation to database."""
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.services.processing_log import ProcessingLogService

        settings = get_settings()
        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        duration = time.time() - start_time

        async with async_session() as session:
            if error:
                await ProcessingLogService.log_llm_error(
                    session, operation, type(error).__name__, str(error),
                    meeting_id, agenda_id, None, provider, {"model": model}
                )
            else:
                await ProcessingLogService.log_llm_complete(
                    session, operation, meeting_id, agenda_id, None,
                    provider, model, duration, prompt_tokens, completion_tokens,
                    prompt_length, response_length
                )
    except Exception as e:
        logger.warning(f"Failed to log LLM operation: {e}")


@dataclass
class MeetingSummary:
    """Result of meeting summary generation."""

    summary: str
    discussions: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    action_items: list[dict[str, Any]]


@dataclass
class QuestionSet:
    """Generated questions for an agenda item."""

    questions: list[str]


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Generate text from a prompt."""
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate JSON response from a prompt."""
        pass


class LLMService:
    """LLM service with provider abstraction."""

    def __init__(self, provider: LLMProvider | None = None):
        self.settings = get_settings()

        if provider is not None:
            self._provider = provider
        else:
            # Auto-select provider based on config
            self._provider = self._create_default_provider()

    def _create_default_provider(self) -> LLMProvider:
        """Create the default LLM provider based on settings."""
        if self.settings.LLM_PROVIDER == "gemini":
            from app.services.gemini import GeminiProvider
            return GeminiProvider(api_key=self.settings.GEMINI_API_KEY)
        elif self.settings.LLM_PROVIDER == "openai":
            from app.services.openai_provider import OpenAIProvider
            return OpenAIProvider(api_key=self.settings.OPENAI_API_KEY)
        else:
            raise ValueError(f"Unknown LLM provider: {self.settings.LLM_PROVIDER}")

    async def generate_meeting_summary(
        self,
        transcript: str,
        agenda_titles: list[str],
        meeting_info: dict[str, Any] | None = None,
        notes: str | None = None,
        sketch_texts: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a meeting summary using LLM.

        Args:
            transcript: Full STT transcript text
            agenda_titles: List of agenda item titles
            meeting_info: Optional meeting metadata (title, date, attendees)
            notes: Optional manual notes
            sketch_texts: Optional extracted text from sketches

        Returns:
            dict with:
                - summary: Overall meeting summary
                - discussions: List of {agenda_id, content} dicts
                - decisions: List of {agenda_id, content, type} dicts
                - action_items: List of {agenda_id, assignee, content, due_date} dicts
        """
        # Transcript length validation
        MAX_TRANSCRIPT_CHARS = 100000
        if transcript and len(transcript) > MAX_TRANSCRIPT_CHARS:
            logger.warning(f"Transcript truncated from {len(transcript)} to {MAX_TRANSCRIPT_CHARS} chars")
            transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n\n[... 내용이 잘림 ...]"

        meeting_type = meeting_info.get('type', 'general') if meeting_info else 'general'

        system_prompt = f"""You are an expert meeting minutes writer with 10+ years of experience in Korean business environments.

Your responsibilities:
1. Extract key discussion points for each agenda item accurately
2. Identify explicit and implicit decisions (including postponed/rejected items)
3. Parse action items with assignee, specific content, and realistic due dates
4. Capture meeting atmosphere and participant engagement
5. Highlight critical insights and turning points

Meeting Type: {meeting_type}

Always respond in Korean with professional business terminology. Be concise but thorough.
"""

        # Build the prompt
        meeting_info_text = ""
        if meeting_info:
            meeting_info_text = f"""
Meeting Information:
- Title: {meeting_info.get('title', 'N/A')}
- Date: {meeting_info.get('scheduled_at', 'N/A')}
- Attendees: {', '.join(meeting_info.get('attendees', []))}
"""

        # Build agenda section with per-agenda transcripts if available
        agenda_info = meeting_info.get('agenda_info', []) if meeting_info else []

        if agenda_info:
            # Use per-agenda transcript info for more accurate summaries
            # Include agenda_id for precise mapping in response
            agendas_parts = []
            for idx, info in enumerate(agenda_info):
                agenda_id = info.get('id', idx)
                level = info.get('level', 0)

                # Use hierarchical_order if available, otherwise compute from order
                order_display = info.get('hierarchical_order', str(info['order'] + 1))

                # 레벨에 따른 제목 형식 (들여쓰기로 구분)
                indent = "  " * level
                agenda_text = f"\n{indent}### 안건 [ID:{agenda_id}] {order_display}: {info['title']}"
                if info.get('transcript'):
                    agenda_text += f"\n[해당 안건 대화 내용]\n{info['transcript']}"
                else:
                    agenda_text += "\n[해당 안건 대화 내용 없음]"
                agendas_parts.append(agenda_text)
            agendas_section = "\n".join(agendas_parts)
        else:
            # Fallback to simple agenda list
            agendas_section = "Agenda Items:\n" + "\n".join(
                f"{i+1}. {title}" for i, title in enumerate(agenda_titles)
            )

        notes_text = f"\nManual Notes:\n{notes}" if notes else ""
        sketch_text = f"\nExtracted Sketch Text:\n{sketch_texts}" if sketch_texts else ""

        # Handle missing or empty transcript
        if transcript and transcript.strip():
            transcript_section = f"\n## 전체 대화 내용 (참고용)\n{transcript}"
            transcript_status = "available"
        else:
            transcript_section = ""
            transcript_status = "no_recording"

        prompt = f"""{meeting_info_text}
## 안건별 대화 내용
{agendas_section}
{transcript_section}
{notes_text}
{sketch_text}

Recording Status: {transcript_status}

Requirements:
1. 안건별로 분리된 대화 내용이 있으면 그것만 기반으로 작성하세요
2. 안건별 대화 내용이 없는 경우("[해당 안건 대화 내용 없음]"), 전체 대화 내용에서 해당 안건과 관련된 부분을 찾아 작성하세요
3. 전체 대화 내용에서도 해당 안건 관련 내용을 찾을 수 없으면 "[논의 내용 없음]"으로 표시하세요
4. 명확한 결정 사항을 식별하세요
5. 실행 항목 추출 (담당자, 내용, 기한)
6. 원본에 없는 내용을 추가하지 마세요
7. JSON 형식으로만 응답하세요
8. 각 안건에 대해 "[ID:숫자]"로 표시된 agenda_id를 반드시 사용하세요 (agenda_idx 대신)
9. 모든 레벨의 안건(대안건, 하위안건, 하하위안건)을 포함하세요
10. summary 필드에는 안건별 요약을 계층 구조로 작성하세요 (예: "## 1. 대안건\n### 1.1 하위안건\n...")

Output format:
{{
  "summary": "Overall meeting summary",
  "transcript_status": "available|no_recording|no_speech",
  "data_sources": ["transcript", "notes", "agenda"],
  "discussions": [{{"agenda_id": 123, "content": "..."}}, ...],
  "decisions": [{{"agenda_id": 123, "content": "...", "type": "approved|postponed|rejected"}}, ...],
  "action_items": [{{"agenda_id": 123, "assignee": "Name", "content": "...", "due_date": "YYYY-MM-DD or null", "priority": "high|medium|low"}}],
  "meeting_insights": {{
    "atmosphere": "positive|neutral|tense",
    "consensus_level": 85,
    "key_turning_points": ["결정적 순간 1", "결정적 순간 2"],
    "top_contributors": ["발언자1", "발언자2", "발언자3"],
    "unresolved_concerns": ["미해결 이슈"]
  }}
}}
"""

        # Get meeting_id from meeting_info for logging
        meeting_id = meeting_info.get('id') if meeting_info else None
        start_time = time.time()
        prompt_length = len(prompt)

        try:
            result = await self._provider.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=self.settings.LLM_MAX_TOKENS_PER_REQUEST,
                temperature=0.3,
            )

            # Log successful operation
            response_str = str(result)
            prompt_tokens = getattr(self._provider, 'last_prompt_tokens', prompt_length // 4)
            completion_tokens = getattr(self._provider, 'last_completion_tokens', len(response_str) // 4)

            asyncio.create_task(log_llm_operation(
                operation="summary",
                meeting_id=meeting_id,
                agenda_id=None,
                provider=self.settings.LLM_PROVIDER,
                model="gemini-2.0-flash",
                start_time=start_time,
                prompt_length=prompt_length,
                response_length=len(response_str),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ))

            # Validate and normalize the response
            return self._normalize_summary_result(result)

        except Exception as e:
            logger.error(f"Failed to generate meeting summary: {e}")
            asyncio.create_task(log_llm_operation(
                operation="summary",
                meeting_id=meeting_id,
                agenda_id=None,
                provider=self.settings.LLM_PROVIDER,
                model="gemini-2.0-flash",
                start_time=start_time,
                prompt_length=prompt_length,
                response_length=0,
                prompt_tokens=0,
                completion_tokens=0,
                error=e,
            ))
            raise

    async def generate_questions(
        self,
        agenda_title: str,
        agenda_description: str | None = None,
        context: str | None = None,
        num_questions: int = 4,
        question_perspective: str | None = None,
    ) -> list[str]:
        """
        Generate discussion questions for an agenda item.

        Args:
            agenda_title: Title of the agenda item
            agenda_description: Optional description of the agenda
            context: Optional additional context
            num_questions: Number of questions to generate (default: 4)
            question_perspective: Optional perspective to guide question generation

        Returns:
            List of question strings
        """
        system_prompt = (
            "You are a meeting facilitation expert. "
            "Generate open-ended questions that help drive productive discussions. "
            "Always respond in Korean."
        )

        description_text = f"\nDescription: {agenda_description}" if agenda_description else ""
        context_text = f"\nAdditional Context: {context}" if context else ""
        perspective_text = ""
        if question_perspective:
            perspective_text = f"""

회의 관점: {question_perspective}
이 관점을 반영하여 참석자들이 실질적으로 고려해야 할 질문을 생성하세요.
"""

        prompt = f"""Generate {num_questions} discussion questions for the following agenda item.

Agenda Title: {agenda_title}{description_text}{context_text}{perspective_text}

Requirements:
1. Questions must be specific and actionable
2. Avoid yes/no questions - use open-ended format
3. Focus on key information needed for decision-making
4. Consider stakeholder perspectives
5. Include at least one question about risks or concerns
6. Respond with a JSON array of strings only

Good Examples:

Agenda: "2024년 예산 검토"
["전년 대비 증감이 큰 항목은 무엇이며, 그 이유는?", "예산 승인 시 고려해야 할 주요 리스크는?", "부서별 예산 배분 기준이 합리적인가?", "예상 외 지출 발생 시 대응 계획은?"]

Agenda: "신규 채용 계획"
["채용이 필요한 포지션과 그 우선순위는?", "현재 인력 운영의 주요 pain point는?", "채용 예산과 타임라인은 어떻게 설정되어 있나?", "채용 실패 시 대안은 무엇인가?"]

Agenda: "프로젝트 진행 상황 점검"
["현재 진행 상황 대비 계획 대비 지연/초과 항목은?", "주요 병목 구간과 해결 방안은?", "다음 마일스톤까지 필요한 리소스는?", "프로젝트 성공을 위해 추가 지원이 필요한 부분은?"]

Now generate questions for the given agenda:
"""

        start_time = time.time()
        prompt_length = len(prompt)

        try:
            result = await self._provider.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=1024,
                temperature=0.7,
            )

            # Handle both array and dict responses
            if isinstance(result, list):
                questions = result
            elif isinstance(result, dict) and "questions" in result:
                questions = result["questions"]
            else:
                logger.warning(f"Unexpected response format: {result}")
                questions = []

            # Log successful operation
            response_str = str(result)
            prompt_tokens = getattr(self._provider, 'last_prompt_tokens', prompt_length // 4)
            completion_tokens = getattr(self._provider, 'last_completion_tokens', len(response_str) // 4)

            asyncio.create_task(log_llm_operation(
                operation="questions",
                meeting_id=None,
                agenda_id=None,
                provider=self.settings.LLM_PROVIDER,
                model="gemini-2.0-flash",
                start_time=start_time,
                prompt_length=prompt_length,
                response_length=len(response_str),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ))

            return [str(q) for q in questions[:num_questions]]

        except Exception as e:
            logger.error(f"Failed to generate questions: {e}")
            asyncio.create_task(log_llm_operation(
                operation="questions",
                meeting_id=None,
                agenda_id=None,
                provider=self.settings.LLM_PROVIDER,
                model="gemini-2.0-flash",
                start_time=start_time,
                prompt_length=prompt_length,
                response_length=0,
                prompt_tokens=0,
                completion_tokens=0,
                error=e,
            ))
            raise

    async def parse_agenda_text(
        self,
        raw_text: str,
        meeting_title: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Parse raw text to extract structured agenda items with hierarchical structure.

        Args:
            raw_text: User-provided text containing agenda items
            meeting_title: Optional meeting title for additional context

        Returns:
            List of dicts with "title", "description", and "children" keys (recursive structure)
        """
        system_prompt = (
            "You are an expert at structuring meeting agendas. "
            "Extract agenda items from text and format them as a hierarchical tree structure. "
            "Always respond in Korean unless the input text is in another language. "
            "Context: The meeting participants are professionals working in the physical education university entrance exam academy industry (체대입시 학원 관련 종사자). "
            "This includes academy owners, PE coaches, admissions consultants, and related staff."
        )

        context_text = f"\nMeeting Context: {meeting_title}" if meeting_title else ""

        prompt = f"""Extract meeting agenda items from the following text and return them as a HIERARCHICAL JSON array.{context_text}

Input Text:
{raw_text}

Requirements:
1. Each agenda item must have:
   - "title" (string): The agenda item title
   - "description" (string or null): Optional detailed description
   - "children" (array): Sub-items as nested agenda objects (same structure, can be empty array)

2. IMPORTANT: Detect hierarchical structure in the input:
   - Main agenda items (numbered like "1.", "2.", "3.") become top-level items
   - Sub-items (indented with "  -", "    *", "  a)", "  1)", etc.) become CHILDREN, not merged into description
   - Deeply nested items become children of children (unlimited depth)

3. **Complex Format Recognition** - Recognize these as hierarchy markers:
   - Level 1: "1.", "I.", "가.", "제1조", "①", "(1)"
   - Level 2: "  -", "  a)", "  1)", "  1항", "> ", "  ㄴ", indented bullets
   - Level 3+: further indentation, "    ㄴ", sub-numbering
   - Korean-style markers: "ㄴ" (ㄴ) is used as a sub-bullet in Korean documents

4. **Contextual Auto-Grouping** - For unstructured input:
   - Group semantically related items under auto-generated parent titles
   - Related questions/topics become children of a group

5. Remove numbering from titles but preserve hierarchy
6. Extract up to 20 main agenda items, unlimited children
7. Preserve the order as they appear

Example 1 (hierarchical structure):
1. 예산안 심의
   - 2024년 예산 검토
   - 비용 절감 방안
     a) 인건비 절감
     b) 운영비 절감
2. 인사 발표

Expected output:
[
  {{
    "title": "예산안 심의",
    "description": null,
    "children": [
      {{"title": "2024년 예산 검토", "description": null, "children": []}},
      {{
        "title": "비용 절감 방안",
        "description": null,
        "children": [
          {{"title": "인건비 절감", "description": null, "children": []}},
          {{"title": "운영비 절감", "description": null, "children": []}}
        ]
      }}
    ]
  }},
  {{"title": "인사 발표", "description": null, "children": []}}
]

Example 2 (Korean legal format):
제1조 회의 목적
   1항 분기 실적 검토
   2항 향후 계획 수립
제2조 예산 승인

Expected output:
[
  {{
    "title": "회의 목적",
    "description": null,
    "children": [
      {{"title": "분기 실적 검토", "description": null, "children": []}},
      {{"title": "향후 계획 수립", "description": null, "children": []}}
    ]
  }},
  {{"title": "예산 승인", "description": null, "children": []}}
]

Example 3 (Korean > and ㄴ markers):
1. 협업 프로그램 안내
 > 1차 협의 내용 공유
 > 상품 메뉴얼
   - 재수종합 + 대치학사
   - 예체능종합 + 체대입시
2. 장학금 이벤트
  ㄴ 장학금 제도 도입
  ㄴ 지점별 1명 전액 장학금

Expected output:
[
  {{
    "title": "협업 프로그램 안내",
    "description": null,
    "children": [
      {{"title": "1차 협의 내용 공유", "description": null, "children": []}},
      {{
        "title": "상품 메뉴얼",
        "description": null,
        "children": [
          {{"title": "재수종합 + 대치학사", "description": null, "children": []}},
          {{"title": "예체능종합 + 체대입시", "description": null, "children": []}}
        ]
      }}
    ]
  }},
  {{
    "title": "장학금 이벤트",
    "description": null,
    "children": [
      {{"title": "장학금 제도 도입", "description": null, "children": []}},
      {{"title": "지점별 1명 전액 장학금", "description": null, "children": []}}
    ]
  }}
]

Example 4 (auto-grouping unstructured):
프로젝트 일정 확인
예산 논의
팀원 충원 계획
기술 스택 결정

Expected output:
[
  {{
    "title": "프로젝트 기획",
    "description": null,
    "children": [
      {{"title": "프로젝트 일정 확인", "description": null, "children": []}},
      {{"title": "예산 논의", "description": null, "children": []}},
      {{"title": "팀원 충원 계획", "description": null, "children": []}}
    ]
  }},
  {{"title": "기술 스택 결정", "description": null, "children": []}}
]

Return a valid JSON array with the hierarchical structure.
"""

        start_time = time.time()
        prompt_length = len(prompt)

        try:
            result = await self._provider.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=4096,
                temperature=0.3,
            )

            # Handle both array and dict responses
            if isinstance(result, list):
                agendas = result
            elif isinstance(result, dict) and "agendas" in result:
                agendas = result["agendas"]
            elif isinstance(result, dict) and "items" in result:
                agendas = result["items"]
            else:
                logger.warning(f"Unexpected response format: {result}")
                agendas = []

            # Recursively validate and normalize agenda items
            def normalize_item(item: dict, depth: int = 0) -> dict | None:
                if not isinstance(item, dict) or "title" not in item:
                    return None
                if depth > 10:  # Prevent infinite recursion
                    return None

                children = []
                if "children" in item and isinstance(item["children"], list):
                    for child in item["children"]:
                        normalized_child = normalize_item(child, depth + 1)
                        if normalized_child:
                            children.append(normalized_child)

                return {
                    "title": str(item["title"]).strip()[:200],
                    "description": str(item.get("description") or "").strip()[:5000] or None,
                    "children": children,
                }

            normalized = []
            for item in agendas[:20]:  # Limit to 20 top-level items
                normalized_item = normalize_item(item)
                if normalized_item:
                    normalized.append(normalized_item)

            # Log successful operation
            response_str = str(result)
            prompt_tokens = getattr(self._provider, 'last_prompt_tokens', prompt_length // 4)
            completion_tokens = getattr(self._provider, 'last_completion_tokens', len(response_str) // 4)

            asyncio.create_task(log_llm_operation(
                operation="agenda_parse",
                meeting_id=None,
                agenda_id=None,
                provider=self.settings.LLM_PROVIDER,
                model="gemini-2.0-flash",
                start_time=start_time,
                prompt_length=prompt_length,
                response_length=len(response_str),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ))

            return normalized

        except Exception as e:
            logger.error(f"Failed to parse agenda text: {e}")
            asyncio.create_task(log_llm_operation(
                operation="agenda_parse",
                meeting_id=None,
                agenda_id=None,
                provider=self.settings.LLM_PROVIDER,
                model="gemini-2.0-flash",
                start_time=start_time,
                prompt_length=prompt_length,
                response_length=0,
                prompt_tokens=0,
                completion_tokens=0,
                error=e,
            ))
            raise

    def _normalize_summary_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Normalize and validate the summary result structure."""
        normalized = {
            "summary": result.get("summary", ""),
            "discussions": [],
            "decisions": [],
            "action_items": [],
        }

        # Normalize discussions - preserve both agenda_id (preferred) and agenda_idx (fallback)
        for item in result.get("discussions", []):
            disc_item = {
                "content": item.get("content", ""),
            }
            # Prefer agenda_id if present, otherwise use agenda_idx
            if "agenda_id" in item:
                disc_item["agenda_id"] = item["agenda_id"]
            else:
                disc_item["agenda_idx"] = item.get("agenda_idx", 0)
            normalized["discussions"].append(disc_item)

        # Normalize decisions
        for item in result.get("decisions", []):
            decision_type = item.get("type", "approved")
            if decision_type not in ("approved", "postponed", "rejected"):
                decision_type = "approved"
            dec_item = {
                "content": item.get("content", ""),
                "type": decision_type,
            }
            if "agenda_id" in item:
                dec_item["agenda_id"] = item["agenda_id"]
            else:
                dec_item["agenda_idx"] = item.get("agenda_idx", 0)
            normalized["decisions"].append(dec_item)

        # Normalize action items
        for item in result.get("action_items", []):
            action_item = {
                "assignee": item.get("assignee", ""),
                "content": item.get("content", ""),
                "due_date": item.get("due_date"),
            }
            if "agenda_id" in item:
                action_item["agenda_id"] = item["agenda_id"]
            else:
                action_item["agenda_idx"] = item.get("agenda_idx", 0)
            normalized["action_items"].append(action_item)

        # Normalize meeting insights
        if "meeting_insights" in result:
            insights = result["meeting_insights"]
            normalized["meeting_insights"] = {
                "atmosphere": insights.get("atmosphere", "neutral"),
                "consensus_level": min(100, max(0, int(insights.get("consensus_level", 50)))),
                "key_turning_points": insights.get("key_turning_points", [])[:5],
                "top_contributors": insights.get("top_contributors", [])[:3],
                "unresolved_concerns": insights.get("unresolved_concerns", []),
            }
        else:
            normalized["meeting_insights"] = {
                "atmosphere": "neutral",
                "consensus_level": 50,
                "key_turning_points": [],
                "top_contributors": [],
                "unresolved_concerns": [],
            }

        return normalized


def get_llm_service() -> LLMService:
    """Get an LLM service instance."""
    return LLMService()


async def generate_meeting_summary(
    transcript: str,
    agenda_titles: list[str],
    meeting_info: dict[str, Any] | None = None,
    notes: str | None = None,
    sketch_texts: str | None = None,
) -> dict[str, Any]:
    """Convenience function to generate meeting summary."""
    service = get_llm_service()
    return await service.generate_meeting_summary(
        transcript=transcript,
        agenda_titles=agenda_titles,
        meeting_info=meeting_info,
        notes=notes,
        sketch_texts=sketch_texts,
    )


async def generate_questions(
    agenda_title: str,
    agenda_description: str | None = None,
    context: str | None = None,
    num_questions: int = 4,
    question_perspective: str | None = None,
) -> list[str]:
    """Convenience function to generate questions."""
    service = get_llm_service()
    return await service.generate_questions(
        agenda_title=agenda_title,
        agenda_description=agenda_description,
        context=context,
        num_questions=num_questions,
        question_perspective=question_perspective,
    )


async def refine_transcript(
    segments: list[dict[str, Any]],
    agenda_titles: list[str],
    attendee_names: list[str] | None = None,
    meeting_title: str | None = None,
) -> list[dict[str, Any]]:
    """
    Refine STT transcript using LLM.

    Improves accuracy by:
    - Correcting proper nouns based on agenda context
    - Matching speakers to attendee names
    - Fixing obvious transcription errors
    - Improving sentence structure
    """
    service = get_llm_service()

    # Build context string
    context_parts = []
    if meeting_title:
        context_parts.append(f"회의 제목: {meeting_title}")
    if agenda_titles:
        context_parts.append(f"안건: {', '.join(agenda_titles)}")
    if attendee_names:
        context_parts.append(f"참석자: {', '.join(attendee_names)}")

    context = "\n".join(context_parts)

    # Build transcript text from segments
    transcript_lines = []
    for seg in segments:
        speaker = seg.get("speaker") or "화자"
        text = seg.get("text", "")
        transcript_lines.append(f"[{speaker}] {text}")

    transcript_text = "\n".join(transcript_lines)

    prompt = f"""다음은 회의 음성을 텍스트로 변환한 결과입니다. 아래 맥락 정보를 참고하여 전사록을 교정해주세요.

## 맥락 정보
{context}

## 교정 지침
1. 고유명사(인명, 기관명, 전문 용어)를 맥락에 맞게 교정
2. 문맥상 어색한 단어나 문장을 자연스럽게 수정
3. 동음이의어 오류 수정 (예: "종라원" → "정노원" 등)
4. 원래 의미를 유지하면서 명확하게 교정

## 원본 전사록
{transcript_text}

## 출력 형식
각 발화를 줄바꿈으로 구분하여 교정된 텍스트만 출력하세요.
[화자] 교정된 텍스트
형식으로 출력하세요.
"""

    try:
        logger.info(f"LLM Service type: {type(service)}, Provider type: {type(service._provider)}")
        refined_text = await service._provider.generate_text(
            prompt=prompt,
            temperature=0.3,  # 낮은 temperature로 일관성 유지
            max_tokens=4096,
        )

        # Parse refined text back to segments
        refined_segments = []
        lines = [line.strip() for line in refined_text.strip().split("\n") if line.strip()]

        # Count non-empty lines for proper ratio mapping
        num_refined = len(lines)
        num_original = len(segments)

        for i, line in enumerate(lines):
            # Parse [speaker] text format
            if line.startswith("[") and "]" in line:
                bracket_end = line.index("]")
                speaker = line[1:bracket_end]
                text = line[bracket_end + 1:].strip()
            else:
                speaker = None
                text = line

            # Map to original segment using ratio-based indexing
            # This ensures timestamps span the full original duration even if line count differs
            if num_original > 0 and num_refined > 0:
                # Calculate the proportional index in original segments
                ratio = i / max(num_refined - 1, 1) if num_refined > 1 else 0
                orig_idx = min(int(ratio * (num_original - 1)), num_original - 1)
                orig = segments[orig_idx]

                # For start/end, interpolate based on position
                if i == 0:
                    start = segments[0].get("start", 0)
                else:
                    prev_ratio = (i - 1) / max(num_refined - 1, 1) if num_refined > 1 else 0
                    prev_orig_idx = min(int(prev_ratio * (num_original - 1)), num_original - 1)
                    start = segments[prev_orig_idx].get("end", 0)

                if i == num_refined - 1:
                    end = segments[-1].get("end", 0)
                else:
                    end = orig.get("end", 0)

                refined_segments.append({
                    "start": start,
                    "end": end,
                    "text": text,
                    "speaker": speaker,
                    "confidence": orig.get("confidence"),
                    "refined": True,
                })
            else:
                refined_segments.append({
                    "start": 0,
                    "end": 0,
                    "text": text,
                    "speaker": speaker,
                    "refined": True,
                })

        logger.info(f"Transcript refined: {len(segments)} -> {len(refined_segments)} segments")
        return refined_segments

    except Exception as e:
        logger.error(f"Failed to refine transcript: {e}")
        # Return original segments on failure
        return segments
