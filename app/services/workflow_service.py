from enum import StrEnum
from typing import Any
from uuid import UUID

from app.api.schemas.workflows import WorkflowResult
from app.services.rag_service import RagService


class WorkflowType(StrEnum):
    SUMMARY = "summary"


class WorkflowExtractionError(RuntimeError):
    """Raised when a workflow result cannot be grounded and validated."""


class WorkflowExtractionService:
    """Builds reviewable workflow results from the existing validated RAG path."""

    def __init__(self, rag_service: RagService) -> None:
        self.rag_service = rag_service

    def extract(self, document_id: UUID, workflow_type: str) -> WorkflowResult:
        if workflow_type != WorkflowType.SUMMARY.value:
            raise WorkflowExtractionError("The requested workflow type is not supported")

        result = self.rag_service.answer(
            "Create a concise summary using only evidence from this document. "
            "Do not infer details that are not supported by the retrieved evidence.",
            document_ids=[str(document_id)],
        )
        if result.abstained or not result.citations:
            raise WorkflowExtractionError("The document does not contain sufficient validated evidence")

        return WorkflowResult(
            summary=result.answer,
            key_points=[],
            citations=[citation.model_dump() for citation in result.citations],
        )
