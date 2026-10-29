from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.services.rag_service import Citation


class WorkflowResult(BaseModel):
    """Structured result stored for the supported summary review task."""

    summary: str = Field(min_length=1, max_length=10000)
    key_points: list[str] = Field(default_factory=list, max_length=20)
    citations: list[Citation] = Field(default_factory=list)


class WorkflowReviewCreate(BaseModel):
    document_id: UUID
    workflow_type: Literal["summary"] = "summary"


class WorkflowReviewDecision(BaseModel):
    reviewer_note: str | None = Field(default=None, max_length=2000)
    edited_summary: str | None = Field(default=None, min_length=1, max_length=10000)
    edited_key_points: list[str] | None = Field(default=None, max_length=20)


class WorkflowReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    workflow_type: str
    structured_result: WorkflowResult
    status: str
    reviewer_decision: str | None
    reviewer_note: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
