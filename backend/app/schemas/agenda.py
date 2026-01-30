"""Agenda-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgendaStatus


# ============================================
# Time Segment Schema
# ============================================


class TimeSegment(BaseModel):
    """Schema for a time segment within an agenda."""

    start: int = Field(..., ge=0, description="Start time in seconds")
    end: int | None = Field(None, ge=0, description="End time in seconds (null if ongoing)")


# ============================================
# Agenda Question Schemas
# ============================================


class QuestionBase(BaseModel):
    """Base schema for agenda questions."""

    question: str = Field(..., min_length=1, max_length=1000)
    order_num: int = Field(default=0, ge=0)
    is_generated: bool = Field(default=True)
    answered: bool = Field(default=False)


class QuestionCreate(QuestionBase):
    """Schema for creating a question."""

    pass


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""

    question: str | None = Field(default=None, min_length=1, max_length=1000)
    order_num: int | None = Field(default=None, ge=0)
    answered: bool | None = None


class QuestionResponse(QuestionBase):
    """Schema for question response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    agenda_id: int


# ============================================
# Agenda Schemas
# ============================================


class AgendaBase(BaseModel):
    """Base schema for agendas."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    order_num: int = Field(default=0, ge=0)
    status: AgendaStatus = Field(default=AgendaStatus.PENDING)


class AgendaCreate(BaseModel):
    """Schema for creating an agenda."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    parent_id: int | None = Field(default=None, description="Parent agenda ID for hierarchical structure")


class AgendaUpdate(BaseModel):
    """Schema for updating an agenda."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    order_num: int | None = Field(default=None, ge=0)
    status: AgendaStatus | None = None
    started_at_seconds: int | None = Field(default=None, ge=0)
    parent_id: int | None = Field(default=None, description="Parent agenda ID (set to move in hierarchy)")
    time_segments: list[TimeSegment] | None = Field(default=None, description="Time segments for multi-segment support")


class AgendaResponse(AgendaBase):
    """Schema for agenda response with hierarchical structure."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    parent_id: int | None = None
    level: int = 0
    started_at_seconds: int | None = None
    time_segments: list[TimeSegment] | None = None
    created_at: datetime
    questions: list[QuestionResponse] = []
    children: list["AgendaResponse"] = []


class AgendaListResponse(BaseModel):
    """Schema for agenda list response."""

    data: list[AgendaResponse]
    meta: dict


# ============================================
# Reorder Schemas
# ============================================


class ReorderItem(BaseModel):
    """Single item for reordering."""

    id: int
    order_num: int = Field(..., ge=0)


class ReorderRequest(BaseModel):
    """Schema for reordering agendas."""

    items: list[ReorderItem] = Field(..., min_length=1)


class ReorderResponse(BaseModel):
    """Schema for reorder response."""

    success: bool = True
    updated_count: int


# ============================================
# Parse Agenda Text Schemas
# ============================================


class AgendaParseRequest(BaseModel):
    """Schema for parsing agenda text."""

    text: str = Field(..., min_length=1, max_length=10000)


class AgendaParseResponse(BaseModel):
    """Schema for parsed agenda response."""

    data: list[AgendaResponse]
    meta: dict


# ============================================
# Parse Preview Schemas (for preview before saving)
# ============================================


class ParsedAgendaItem(BaseModel):
    """Single parsed agenda item (preview, not saved) with hierarchical structure."""

    title: str
    description: str | None = None
    children: list["ParsedAgendaItem"] = []


class AgendaParsePreviewResponse(BaseModel):
    """Schema for parsed agenda preview response."""

    items: list[ParsedAgendaItem]
    meta: dict


# ============================================
# Move Agenda Schemas (for hierarchy operations)
# ============================================


class AgendaMoveRequest(BaseModel):
    """Schema for moving an agenda in the hierarchy."""

    new_parent_id: int | None = Field(
        default=None,
        description="New parent ID. Set to null to move to root level."
    )
    new_order_num: int = Field(
        ...,
        ge=0,
        description="New order within the parent (or root level)"
    )


class AgendaMoveResponse(BaseModel):
    """Schema for move agenda response."""

    success: bool = True
    agenda: "AgendaResponse"


# Rebuild models for forward references
AgendaResponse.model_rebuild()
ParsedAgendaItem.model_rebuild()
AgendaMoveResponse.model_rebuild()
