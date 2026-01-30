"""Search service for full-text search using pg_trgm."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.meeting import Meeting
from app.models.recording import Transcript
from app.models.result import MeetingResult


class SearchService:
    """Service for searching across meetings, contacts, and transcripts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_all(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """
        Search across all searchable entities using pg_trgm similarity.

        Args:
            query: Search query string
            limit: Maximum results per type
            offset: Offset for pagination

        Returns:
            Dictionary with meetings, contacts, and transcripts results
        """
        # Search in parallel
        meetings = await self._search_meetings(query, limit, offset)
        contacts = await self._search_contacts(query, limit, offset)
        transcripts = await self._search_transcripts(query, limit, offset)

        return {
            "meetings": meetings,
            "contacts": contacts,
            "transcripts": transcripts,
        }

    async def _search_meetings(
        self,
        query: str,
        limit: int,
        offset: int,
    ) -> list[dict]:
        """
        Search meetings by summary using pg_trgm similarity.

        Searches in meeting_results.summary field.
        """
        # Use similarity function from pg_trgm
        # similarity() returns a score between 0 and 1
        similarity_expr = func.similarity(MeetingResult.summary, query)

        stmt = (
            select(
                Meeting.id,
                Meeting.title,
                Meeting.scheduled_at,
                Meeting.status,
                MeetingResult.summary,
                similarity_expr.label("match_score"),
            )
            .join(MeetingResult, Meeting.id == MeetingResult.meeting_id)
            .where(
                Meeting.deleted_at.is_(None),
                # similarity threshold (0.3 is reasonable for trigram matching)
                similarity_expr > 0.1,
            )
            .order_by(similarity_expr.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "id": row.id,
                "title": row.title,
                "scheduled_at": row.scheduled_at,
                "status": row.status,
                "highlight": self._create_highlight(row.summary, query),
                "match_score": float(row.match_score),
            }
            for row in rows
        ]

    async def _search_contacts(
        self,
        query: str,
        limit: int,
        offset: int,
    ) -> list[dict]:
        """
        Search contacts by name using pg_trgm similarity.
        """
        similarity_expr = func.similarity(Contact.name, query)

        stmt = (
            select(
                Contact.id,
                Contact.name,
                Contact.organization,
                Contact.role,
                similarity_expr.label("match_score"),
            )
            .where(
                Contact.deleted_at.is_(None),
                similarity_expr > 0.1,
            )
            .order_by(similarity_expr.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "id": row.id,
                "name": row.name,
                "organization": row.organization,
                "role": row.role,
                "highlight": self._create_highlight(row.name, query),
                "match_score": float(row.match_score),
            }
            for row in rows
        ]

    async def _search_transcripts(
        self,
        query: str,
        limit: int,
        offset: int,
    ) -> list[dict]:
        """
        Search transcripts by full_text using pg_trgm similarity.

        Note: Transcripts table has a full_text column that contains the complete text.
        """
        # Query transcripts table directly using the full_text column
        # We need to add the column reference to the model
        from sqlalchemy import column

        # Use the full_text column from the transcripts table
        full_text_col = column("full_text")
        similarity_expr = func.similarity(full_text_col, query)

        stmt = (
            select(
                Transcript.id,
                Transcript.meeting_id,
                Transcript.chunk_index,
                Transcript.created_at,
                full_text_col.label("full_text"),
                Meeting.title.label("meeting_title"),
                similarity_expr.label("match_score"),
            )
            .select_from(Transcript)
            .join(Meeting, Transcript.meeting_id == Meeting.id)
            .where(
                Meeting.deleted_at.is_(None),
                full_text_col.isnot(None),
                similarity_expr > 0.1,
            )
            .order_by(similarity_expr.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "id": row.id,
                "meeting_id": row.meeting_id,
                "meeting_title": row.meeting_title,
                "chunk_index": row.chunk_index,
                "highlight": self._create_highlight(row.full_text, query),
                "match_score": float(row.match_score),
                "created_at": row.created_at,
            }
            for row in rows
        ]

    def _create_highlight(
        self,
        text: str | None,
        query: str,
        context_length: int = 100,
    ) -> str | None:
        """
        Create a highlighted snippet from the text.

        Args:
            text: The full text to search in
            query: The search query
            context_length: Characters to show before/after match

        Returns:
            Highlighted snippet or None if no text
        """
        if not text:
            return None

        # Find the position of the query (case-insensitive)
        text_lower = text.lower()
        query_lower = query.lower()
        pos = text_lower.find(query_lower)

        if pos == -1:
            # If exact match not found, return first N characters
            return text[:context_length * 2] + ("..." if len(text) > context_length * 2 else "")

        # Calculate snippet boundaries
        start = max(0, pos - context_length)
        end = min(len(text), pos + len(query) + context_length)

        # Extract snippet
        snippet = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet
