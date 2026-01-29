"""Search API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.schemas.search import (
    ContactSearchResult,
    MeetingSearchResult,
    SearchMeta,
    SearchResponse,
    SearchResults,
    TranscriptSearchResult,
)
from app.services.search import SearchService


router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Search query string",
        alias="q",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of results per type",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of results to skip",
    ),
):
    """
    Search across meetings, contacts, and transcripts.

    Uses PostgreSQL pg_trgm (trigram) similarity matching for fuzzy search.

    - **q**: Search query string (required)
    - **limit**: Maximum results per type (1-100, default 20)
    - **offset**: Pagination offset

    Returns results grouped by type:
    - **meetings**: Matches in meeting summaries
    - **contacts**: Matches in contact names
    - **transcripts**: Matches in transcript text

    Each result includes:
    - Relevance score (0-1)
    - Highlighted snippet showing the match context
    """
    service = SearchService(db)
    results = await service.search_all(
        query=q,
        limit=limit,
        offset=offset,
    )

    # Convert to response schemas
    meetings = [
        MeetingSearchResult(**result)
        for result in results["meetings"]
    ]
    contacts = [
        ContactSearchResult(**result)
        for result in results["contacts"]
    ]
    transcripts = [
        TranscriptSearchResult(**result)
        for result in results["transcripts"]
    ]

    total = len(meetings) + len(contacts) + len(transcripts)

    return SearchResponse(
        data=SearchResults(
            meetings=meetings,
            contacts=contacts,
            transcripts=transcripts,
        ),
        meta=SearchMeta(
            query=q,
            total=total,
            limit=limit,
            offset=offset,
        ),
    )
