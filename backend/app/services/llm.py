"""
LLM service abstraction layer.

Provides a unified interface for LLM providers (Gemini, OpenAI).
Based on spec Section 9 (LLM Prompt Strategy).
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


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

        agendas_text = "\n".join(
            f"{i+1}. {title}" for i, title in enumerate(agenda_titles)
        )

        notes_text = f"\nManual Notes:\n{notes}" if notes else ""
        sketch_text = f"\nExtracted Sketch Text:\n{sketch_texts}" if sketch_texts else ""

        prompt = f"""{meeting_info_text}
Agenda Items:
{agendas_text}

STT Transcript:
{transcript}
{notes_text}
{sketch_text}

Requirements:
1. Summarize discussion content for each agenda item
2. Clearly identify decisions made
3. Extract action items (assignee, content, due date if mentioned)
4. Do not add information not present in the source materials
5. Respond in JSON format only
6. Analyze meeting atmosphere (positive/neutral/tense)
7. Identify key turning points in the discussion
8. Note consensus level (0-100)
9. Summarize top 3 speaker contributions

Output format:
{{
  "summary": "Overall meeting summary",
  "discussions": [{{"agenda_idx": 0, "content": "..."}}, ...],
  "decisions": [{{"agenda_idx": 0, "content": "...", "type": "approved|postponed|rejected"}}, ...],
  "action_items": [{{"agenda_idx": 0, "assignee": "Name", "content": "...", "due_date": "YYYY-MM-DD or null", "priority": "high|medium|low"}}],
  "meeting_insights": {{
    "atmosphere": "positive|neutral|tense",
    "consensus_level": 85,
    "key_turning_points": ["결정적 순간 1", "결정적 순간 2"],
    "top_contributors": ["발언자1", "발언자2", "발언자3"],
    "unresolved_concerns": ["미해결 이슈"]
  }}
}}
"""

        try:
            result = await self._provider.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=self.settings.LLM_MAX_TOKENS_PER_REQUEST,
                temperature=0.3,
            )

            # Validate and normalize the response
            return self._normalize_summary_result(result)

        except Exception as e:
            logger.error(f"Failed to generate meeting summary: {e}")
            raise

    async def generate_questions(
        self,
        agenda_title: str,
        agenda_description: str | None = None,
        context: str | None = None,
        num_questions: int = 4,
    ) -> list[str]:
        """
        Generate discussion questions for an agenda item.

        Args:
            agenda_title: Title of the agenda item
            agenda_description: Optional description of the agenda
            context: Optional additional context
            num_questions: Number of questions to generate (default: 4)

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

        prompt = f"""Generate {num_questions} discussion questions for the following agenda item.

Agenda Title: {agenda_title}{description_text}{context_text}

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

            return [str(q) for q in questions[:num_questions]]

        except Exception as e:
            logger.error(f"Failed to generate questions: {e}")
            raise

    async def parse_agenda_text(
        self,
        raw_text: str,
        meeting_title: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Parse raw text to extract structured agenda items.

        Args:
            raw_text: User-provided text containing agenda items
            meeting_title: Optional meeting title for additional context

        Returns:
            List of dicts with "title" and "description" keys
        """
        system_prompt = (
            "You are an expert at structuring meeting agendas. "
            "Extract agenda items from text and format them consistently. "
            "Always respond in Korean unless the input text is in another language."
        )

        context_text = f"\nMeeting Context: {meeting_title}" if meeting_title else ""

        prompt = f"""Extract meeting agenda items from the following text and return them as a structured JSON array.{context_text}

Input Text:
{raw_text}

Requirements:
1. Each agenda item must have "title" (string) and "description" (string) fields
2. IMPORTANT: Detect hierarchical structure in the input:
   - Main agenda items (numbered like "1.", "2.", "3." or top-level bullets) become separate agendas
   - Sub-items (indented, using "  -", "    *", "  a)", "  1)", etc.) are NOT separate agendas
   - Sub-items should be merged into the parent agenda's "description" field
   - Keep sub-item formatting (bullet points, dashes) in the description for readability
3. **Complex Format Recognition** - Recognize these numbering systems as main agenda markers:
   - Roman numerals: "I.", "II.", "III." or "i.", "ii.", "iii."
   - Korean numbering: "가.", "나.", "다." or "ㄱ.", "ㄴ.", "ㄷ."
   - Korean legal format: "제1조", "제2조", "제1항", "제2항"
   - Circled numbers: "①", "②", "③" or "㉠", "㉡", "㉢"
   - Parenthetical: "(1)", "(a)", "1)", "a)"
4. **Contextual Auto-Grouping** - For unstructured input (no clear numbering or bullets):
   - Group semantically related items together (e.g., related questions, similar topics)
   - Generate a meaningful group title automatically from the content
   - Place individual related items into the description field
5. Remove numbering or bullet points from main titles only
6. If no description or sub-items exist, use an empty string for description
7. Extract up to 20 main agenda items maximum
8. Preserve the order of items as they appear in the text
9. Do not add information that is not present in the source text

Example 1 (basic numbered list):
1. 예산안 심의
   - 2024년 예산 검토
   - 비용 절감 방안 논의
2. 인사 발표
   - 신규 채용 현황
3. 기타 안건

Expected output:
[
  {{"title": "예산안 심의", "description": "- 2024년 예산 검토\\n- 비용 절감 방안 논의"}},
  {{"title": "인사 발표", "description": "- 신규 채용 현황"}},
  {{"title": "기타 안건", "description": ""}}
]

Example 2 (Roman numerals):
I. Quarterly Financial Review
   - Revenue analysis
   - Budget variance report
II. Product Launch Plan
III. Marketing Strategy

Expected output:
[
  {{"title": "Quarterly Financial Review", "description": "- Revenue analysis\\n- Budget variance report"}},
  {{"title": "Product Launch Plan", "description": ""}},
  {{"title": "Marketing Strategy", "description": ""}}
]

Example 3 (Korean legal format):
제1조 회의 목적
   1항 분기 실적 검토
   2항 향후 계획 수립
제2조 예산 승인
   1항 예산안 심의
   2항 집행 계획 확정

Expected output:
[
  {{"title": "회의 목적", "description": "1항 분기 실적 검토\\n2항 향후 계획 수립"}},
  {{"title": "예산 승인", "description": "1항 예산안 심의\\n2항 집행 계획 확정"}}
]

Example 4 (unstructured list with auto-grouping):
프로젝트 일정은 어떻게 되나요?
예산은 충분한가요?
팀원 충원 계획은?
기술 스택은 확정되었나요?
보안 검토는 완료되었나요?

Expected output:
[
  {{"title": "프로젝트 기획 및 자원", "description": "- 프로젝트 일정은 어떻게 되나요?\\n- 예산은 충분한가요?\\n- 팀원 충원 계획은?"}},
  {{"title": "기술 및 보안", "description": "- 기술 스택은 확정되었나요?\\n- 보안 검토는 완료되었나요?"}}
]

Output format:
[
  {{"title": "Budget Review", "description": "- Review Q4 budget allocation\\n- Discuss cost savings"}},
  {{"title": "New Project Approval", "description": ""}}
]
"""

        try:
            result = await self._provider.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=2048,
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

            # Validate and normalize each agenda item
            normalized = []
            for item in agendas[:20]:  # Limit to 20 items
                if isinstance(item, dict) and "title" in item:
                    normalized.append({
                        "title": str(item["title"]).strip()[:200],  # Max 200 chars
                        "description": str(item.get("description", "")).strip()[:5000],  # Max 5000 chars
                    })

            return normalized

        except Exception as e:
            logger.error(f"Failed to parse agenda text: {e}")
            raise

    def _normalize_summary_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Normalize and validate the summary result structure."""
        normalized = {
            "summary": result.get("summary", ""),
            "discussions": [],
            "decisions": [],
            "action_items": [],
        }

        # Normalize discussions
        for item in result.get("discussions", []):
            normalized["discussions"].append({
                "agenda_idx": item.get("agenda_idx", item.get("agenda_id", 0)),
                "content": item.get("content", ""),
            })

        # Normalize decisions
        for item in result.get("decisions", []):
            decision_type = item.get("type", "approved")
            if decision_type not in ("approved", "postponed", "rejected"):
                decision_type = "approved"
            normalized["decisions"].append({
                "agenda_idx": item.get("agenda_idx", item.get("agenda_id", 0)),
                "content": item.get("content", ""),
                "type": decision_type,
            })

        # Normalize action items
        for item in result.get("action_items", []):
            normalized["action_items"].append({
                "agenda_idx": item.get("agenda_idx", item.get("agenda_id", 0)),
                "assignee": item.get("assignee", ""),
                "content": item.get("content", ""),
                "due_date": item.get("due_date"),
            })

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
) -> list[str]:
    """Convenience function to generate questions."""
    service = get_llm_service()
    return await service.generate_questions(
        agenda_title=agenda_title,
        agenda_description=agenda_description,
        context=context,
        num_questions=num_questions,
    )
