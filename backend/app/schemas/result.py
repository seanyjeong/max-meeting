"""Meeting result-related Pydantic schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ActionItemPriority,
    ActionItemStatus,
    DecisionType,
)


# ============================================
# Action Item Schemas
# ============================================


class ActionItemBase(BaseModel):
    """Base schema for action items."""

    content: str = Field(..., min_length=1, max_length=2000)
    due_date: date | None = None
    priority: ActionItemPriority = Field(default=ActionItemPriority.MEDIUM)
    status: ActionItemStatus = Field(default=ActionItemStatus.PENDING)


class ActionItemCreate(BaseModel):
    """Schema for creating an action item."""

    content: str = Field(..., min_length=1, max_length=2000)
    agenda_id: int | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    priority: ActionItemPriority = Field(default=ActionItemPriority.MEDIUM)


class ActionItemUpdate(BaseModel):
    """Schema for updating an action item."""

    content: str | None = Field(default=None, min_length=1, max_length=2000)
    agenda_id: int | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    priority: ActionItemPriority | None = None
    status: ActionItemStatus | None = None


class ActionItemResponse(ActionItemBase):
    """Schema for action item response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    agenda_id: int | None
    assignee_id: int | None
    completed_at: datetime | None
    created_at: datetime


# ============================================
# Decision Schemas
# ============================================


class DecisionBase(BaseModel):
    """Base schema for decisions."""

    content: str = Field(..., min_length=1, max_length=2000)
    decision_type: DecisionType = Field(default=DecisionType.APPROVED)


class DecisionCreate(DecisionBase):
    """Schema for creating a decision."""

    agenda_id: int | None = None


class DecisionResponse(DecisionBase):
    """Schema for decision response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    agenda_id: int | None
    created_at: datetime


# ============================================
# Discussion Schemas
# ============================================


class DiscussionBase(BaseModel):
    """Base schema for discussions."""

    content: str = Field(..., min_length=1, max_length=10000)
    is_llm_generated: bool = Field(default=True)


class DiscussionResponse(DiscussionBase):
    """Schema for discussion response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    agenda_id: int
    version: int
    created_at: datetime
    updated_at: datetime


# ============================================
# Meeting Result Schemas
# ============================================


class ResultBase(BaseModel):
    """Base schema for meeting results."""

    summary: str | None = Field(default=None, max_length=10000)


class ResultCreate(BaseModel):
    """Schema for creating a meeting result."""

    summary: str | None = Field(default=None, max_length=10000)
    key_points: list[str] | None = None


class ResultUpdate(BaseModel):
    """Schema for updating a meeting result."""

    summary: str | None = Field(default=None, max_length=10000)
    key_points: list[str] | None = None


class ResultResponse(ResultBase):
    """Schema for meeting result response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    is_verified: bool
    verified_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class ResultDetailResponse(ResultResponse):
    """Schema for detailed meeting result with related data."""

    decisions: list[DecisionResponse] = []
    action_items: list[ActionItemResponse] = []


class ResultVersionListResponse(BaseModel):
    """Schema for listing result versions."""

    data: list[ResultResponse]
    meta: dict


# ============================================
# Regeneration Schemas
# ============================================


class RegenerateRequest(BaseModel):
    """Schema for triggering LLM regeneration."""

    include_transcript: bool = Field(default=True)
    include_notes: bool = Field(default=True)
    include_sketches: bool = Field(default=False)
    custom_prompt: str | None = Field(default=None, max_length=2000)


class RegenerateResponse(BaseModel):
    """Response for regeneration request."""

    task_id: str
    message: str = "Regeneration task started"
