"""Schemas for segment analysis API."""

from pydantic import BaseModel, Field


class AnalyzeSegmentsRequest(BaseModel):
    """Request to analyze segments for agenda mismatches."""

    force_reanalyze: bool = Field(
        default=False,
        description="If true, re-analyze segments that already have suggestions",
    )


class SegmentSuggestionResponse(BaseModel):
    """A single segment suggestion."""

    segment_index: int
    segment_text: str
    current_agenda_id: int | None
    current_agenda_title: str | None
    suggested_agenda_id: int | None
    suggested_agenda_title: str | None
    confidence: float
    reason: str


class AnalyzeSegmentsResponse(BaseModel):
    """Response from segment analysis."""

    total_segments: int
    analyzed: int
    mismatches_found: int
    suggestions: list[SegmentSuggestionResponse]
    error: str | None = None


class MoveSegmentRequest(BaseModel):
    """Request to move a segment to a different agenda."""

    target_agenda_id: int = Field(..., description="ID of the agenda to move the segment to")
    accept_suggestion: bool = Field(
        default=True,
        description="Whether this is accepting a suggestion (true) or rejecting (false)",
    )


class MoveSegmentResponse(BaseModel):
    """Response from moving a segment."""

    success: bool
    segment_index: int | None = None
    moved_to_agenda_id: int | None = None
    time_segments_updated: bool = False
    error: str | None = None


class BulkMoveAction(BaseModel):
    """A single action in bulk move."""

    segment_index: int
    accept: bool
    override_agenda_id: int | None = Field(
        default=None,
        description="If provided, move to this agenda instead of the suggested one",
    )


class BulkMoveRequest(BaseModel):
    """Request for bulk segment moves."""

    actions: list[BulkMoveAction]


class BulkMoveResponse(BaseModel):
    """Response from bulk segment moves."""

    success: bool
    processed: int
    succeeded: int
    failed: int
    errors: list[str] = []
