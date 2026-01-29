"""
Speaker analytics service for advanced meeting participant analysis.

Provides sentiment analysis, engagement scoring, and contribution tracking.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SpeakerStats:
    """Statistics for a single speaker in a meeting."""

    speaker_id: str
    total_speaking_time: float = 0.0
    turn_count: int = 0
    questions_asked: int = 0
    statements_made: int = 0
    sentiment_score: float = 0.0  # -1.0 (negative) to 1.0 (positive)
    engagement_score: float = 0.0  # 0 to 100
    dominant_topics: list[str] = field(default_factory=list)
    avg_turn_length: float = 0.0


class SpeakerAnalyticsService:
    """Service for analyzing speaker contributions and sentiment."""

    def __init__(self, llm_service: Any | None = None):
        """Initialize with optional LLM service for advanced analysis."""
        self._llm_service = llm_service

    async def analyze_speakers(
        self,
        segments: list[dict[str, Any]],
        speakers: list[str] | None = None,
    ) -> dict[str, SpeakerStats]:
        """
        Analyze speaker contributions from transcript segments.

        Args:
            segments: List of transcript segments with speaker, text, start, end
            speakers: Optional list of speaker IDs to analyze

        Returns:
            Dict mapping speaker_id to SpeakerStats
        """
        if not segments:
            return {}

        # Extract unique speakers if not provided
        if speakers is None:
            speakers = list(set(seg.get('speaker', 'Unknown') for seg in segments))

        analytics: dict[str, SpeakerStats] = {}

        for speaker in speakers:
            speaker_segments = [
                s for s in segments
                if s.get('speaker') == speaker
            ]

            if not speaker_segments:
                continue

            # Calculate basic metrics
            total_time = sum(
                s.get('end', 0) - s.get('start', 0)
                for s in speaker_segments
            )
            combined_text = " ".join(s.get('text', '') for s in speaker_segments)

            # Count questions (Korean and English)
            questions = self._count_questions(combined_text)

            # Count statements (non-questions)
            statements = len(speaker_segments) - questions

            # Calculate sentiment (rule-based for now, LLM upgrade later)
            sentiment = await self._analyze_sentiment(combined_text)

            # Calculate engagement score
            engagement = self._calculate_engagement(
                total_time=total_time,
                turn_count=len(speaker_segments),
                questions=questions,
                total_segments=len(segments),
            )

            # Extract dominant topics
            topics = self._extract_topics(combined_text)

            analytics[speaker] = SpeakerStats(
                speaker_id=speaker,
                total_speaking_time=round(total_time, 2),
                turn_count=len(speaker_segments),
                questions_asked=questions,
                statements_made=max(0, statements),
                sentiment_score=round(sentiment, 2),
                engagement_score=round(engagement, 1),
                dominant_topics=topics[:5],
                avg_turn_length=round(total_time / len(speaker_segments), 2) if speaker_segments else 0,
            )

        return analytics

    def _count_questions(self, text: str) -> int:
        """Count question sentences in text."""
        # Korean question endings
        korean_patterns = [
            r'[가-힣]+\s*\?',  # Ends with ?
            r'[습니까][\s\?\.]',  # formal question ending
            r'[는지][\s\?\.]',  # indirect question
            r'[나요][\s\?\.]',  # polite question
            r'[까요][\s\?\.]',  # polite question
            r'[을까][\s\?\.]',  # suggestion question
            r'어때[요]?[\s\?\.]',  # "how about" question
        ]

        # English question pattern
        english_pattern = r'\b(what|when|where|who|why|how|is|are|do|does|can|could|would|should)\b.*\?'

        count = 0

        # Count Korean questions
        for pattern in korean_patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))

        # Count English questions
        count += len(re.findall(english_pattern, text, re.IGNORECASE))

        # Count explicit question marks
        explicit_questions = text.count('?')

        # Use the higher count (avoid double counting)
        return max(count, explicit_questions)

    async def _analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of text.

        Returns value between -1.0 (negative) and 1.0 (positive).
        """
        if not text:
            return 0.0

        # Use LLM if available for more accurate analysis
        if self._llm_service:
            try:
                # Try to use generate_json method if available on provider
                provider = getattr(self._llm_service, '_provider', None)
                if provider and hasattr(provider, 'generate_json'):
                    result = await provider.generate_json(
                        prompt=f"""Analyze the sentiment of this Korean speech:

"{text[:2000]}"

Return ONLY a JSON object:
{{"sentiment": float between -1 (very negative) and 1 (very positive)}}

Consider:
- Positive: agreement, enthusiasm, support, satisfaction
- Negative: disagreement, frustration, concern, criticism
- Neutral: factual statements, questions, procedural talk
""",
                        temperature=0.3,
                        max_tokens=64,
                    )
                    return max(-1.0, min(1.0, float(result.get('sentiment', 0.0))))
            except Exception as e:
                logger.warning(f"LLM sentiment analysis failed, using rule-based: {e}")

        # Rule-based fallback
        positive_words = [
            '좋', '훌륭', '잘', '감사', '동의', '찬성', '긍정', '성공', '발전',
            '개선', '향상', '효과', 'good', 'great', 'agree', 'yes', 'excellent',
            '완료', '해결', '달성', '기대', '희망', '환영',
        ]
        negative_words = [
            '문제', '어려', '걱정', '반대', '부정', '실패', '지연', '우려',
            '불만', '아쉬', 'bad', 'issue', 'problem', 'disagree', 'no', 'concern',
            '불가', '위험', '손실', '부족', '지적',
        ]

        text_lower = text.lower()

        positive_count = sum(1 for w in positive_words if w in text_lower)
        negative_count = sum(1 for w in negative_words if w in text_lower)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        # Calculate score: (positive - negative) / total, normalized to -1 to 1
        score = (positive_count - negative_count) / total
        return max(-1.0, min(1.0, score))

    def _calculate_engagement(
        self,
        total_time: float,
        turn_count: int,
        questions: int,
        total_segments: int,
    ) -> float:
        """
        Calculate engagement score (0-100) based on participation metrics.
        """
        if total_segments == 0:
            return 0.0

        # Participation ratio (how much of the conversation they contributed)
        participation_ratio = turn_count / total_segments

        # Question ratio (asking questions shows engagement)
        question_ratio = questions / max(1, turn_count)

        # Base score from participation (0-60 points)
        participation_score = min(60, participation_ratio * 120)  # Max 60 for 50% participation

        # Question bonus (0-20 points)
        question_score = min(20, question_ratio * 40)  # Max 20 for 50% questions

        # Turn frequency bonus (0-20 points) - more turns = more engaged
        turn_score = min(20, turn_count * 2)  # Max 20 for 10+ turns

        total_score = participation_score + question_score + turn_score

        return min(100, total_score)

    def _extract_topics(self, text: str) -> list[str]:
        """
        Extract dominant topics/keywords from text.

        Simple keyword extraction - can be enhanced with TF-IDF or LLM.
        """
        if not text:
            return []

        # Remove common stop words
        stop_words = {
            '그', '저', '이', '것', '수', '있', '하', '등', '및', '를', '을',
            '가', '이', '는', '에', '로', '로서', '대해', '위해', '통해',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            '합니다', '입니다', '있습니다', '됩니다', '했습니다',
        }

        # Simple word frequency
        words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', text)
        word_freq: dict[str, int] = {}

        for word in words:
            word_lower = word.lower()
            if word_lower not in stop_words and len(word_lower) >= 2:
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1

        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        return [word for word, _ in sorted_words[:10]]

    def get_meeting_speaker_summary(
        self,
        analytics: dict[str, SpeakerStats],
    ) -> dict[str, Any]:
        """
        Generate a summary of all speakers in the meeting.
        """
        if not analytics:
            return {
                "total_speakers": 0,
                "most_active_speaker": None,
                "most_positive_speaker": None,
                "most_engaged_speaker": None,
                "average_sentiment": 0.0,
                "participation_balance": 0.0,
            }

        speakers = list(analytics.values())

        # Find top speakers
        most_active = max(speakers, key=lambda s: s.total_speaking_time)
        most_positive = max(speakers, key=lambda s: s.sentiment_score)
        most_engaged = max(speakers, key=lambda s: s.engagement_score)

        # Calculate averages
        avg_sentiment = sum(s.sentiment_score for s in speakers) / len(speakers)

        # Participation balance (0-100, higher = more balanced)
        total_time = sum(s.total_speaking_time for s in speakers)
        if total_time > 0 and len(speakers) > 1:
            expected_share = 1 / len(speakers)
            deviations = sum(
                abs((s.total_speaking_time / total_time) - expected_share)
                for s in speakers
            )
            # Max deviation would be 2 * (1 - 1/n) for n speakers
            max_deviation = 2 * (1 - expected_share)
            balance = max(0, 100 * (1 - deviations / max_deviation))
        else:
            balance = 100.0 if len(speakers) == 1 else 0.0

        return {
            "total_speakers": len(speakers),
            "most_active_speaker": most_active.speaker_id,
            "most_positive_speaker": most_positive.speaker_id,
            "most_engaged_speaker": most_engaged.speaker_id,
            "average_sentiment": round(avg_sentiment, 2),
            "participation_balance": round(balance, 1),
        }


def get_speaker_analytics_service(llm_service: Any | None = None) -> SpeakerAnalyticsService:
    """Get a speaker analytics service instance."""
    return SpeakerAnalyticsService(llm_service=llm_service)
