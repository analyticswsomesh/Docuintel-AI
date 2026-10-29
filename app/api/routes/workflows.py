from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_document_repository,
    get_workflow_extraction_service,
    get_workflow_review_repository,
)
from app.api.schemas.workflows import WorkflowResult, WorkflowReviewCreate, WorkflowReviewDecision, WorkflowReviewRead
from app.db.models import WorkflowReview
from app.db.repositories import (
    DocumentRepository,
    DocumentRepositoryError,
    WorkflowReviewRepository,
    WorkflowReviewRepositoryError,
)
from app.services.workflow_service import WorkflowExtractionError, WorkflowExtractionService


router = APIRouter(prefix="/api/reviews", tags=["workflow-reviews"])
DocumentDependency = Annotated[DocumentRepository, Depends(get_document_repository)]
ReviewDependency = Annotated[WorkflowReviewRepository, Depends(get_workflow_review_repository)]
WorkflowDependency = Annotated[WorkflowExtractionService, Depends(get_workflow_extraction_service)]


def _read_result(review: WorkflowReview) -> WorkflowResult:
    return WorkflowResult.model_validate(review.structured_result)


@router.post("", response_model=WorkflowReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(
    request: WorkflowReviewCreate,
    documents: DocumentDependency,
    reviews: ReviewDependency,
    workflow_service: WorkflowDependency,
) -> WorkflowReview:
    document = documents.get(request.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "indexed":
        raise HTTPException(status_code=409, detail="The document must be indexed before review")

    try:
        result = workflow_service.extract(request.document_id, request.workflow_type)
    except WorkflowExtractionError as error:
        try:
            failed = reviews.create(
                document_id=request.document_id,
                workflow_type=request.workflow_type,
                structured_result={"summary": "Workflow extraction failed", "key_points": [], "citations": []},
                status="failed",
                error_message=str(error)[:500],
            )
        except WorkflowReviewRepositoryError as persistence_error:
            raise HTTPException(status_code=503, detail="Workflow review could not be stored") from persistence_error
        raise HTTPException(
            status_code=422,
            detail={"message": "Workflow extraction failed", "review_id": str(failed.id), "status": failed.status},
        ) from error

    try:
        return reviews.create(
            document_id=request.document_id,
            workflow_type=request.workflow_type,
            structured_result=result.model_dump(mode="json"),
        )
    except WorkflowReviewRepositoryError as error:
        raise HTTPException(status_code=503, detail="Workflow review could not be stored") from error


@router.get("", response_model=list[WorkflowReviewRead])
def list_reviews(
    reviews: ReviewDependency,
    document_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[WorkflowReview]:
    try:
        return list(reviews.list(document_id=document_id, limit=limit, offset=offset))
    except WorkflowReviewRepositoryError as error:
        raise HTTPException(status_code=503, detail="Workflow reviews could not be loaded") from error


@router.get("/{review_id}", response_model=WorkflowReviewRead)
def get_review(review_id: UUID, reviews: ReviewDependency) -> WorkflowReview:
    review = reviews.get(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Workflow review not found")
    return review


@router.post("/{review_id}/approve", response_model=WorkflowReviewRead)
def approve_review(review_id: UUID, request: WorkflowReviewDecision, reviews: ReviewDependency) -> WorkflowReview:
    review = reviews.get(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Workflow review not found")
    if review.status != "pending_review":
        raise HTTPException(status_code=409, detail="Only pending reviews can be approved")

    result = _read_result(review)
    if request.edited_summary is not None:
        result.summary = request.edited_summary
    if request.edited_key_points is not None:
        result.key_points = request.edited_key_points
    if not result.citations:
        raise HTTPException(status_code=422, detail="A review cannot be approved without evidence citations")

    try:
        updated = reviews.decide(
            review_id,
            status="approved",
            reviewer_decision="approved",
            reviewer_note=request.reviewer_note,
            structured_result=result.model_dump(mode="json"),
        )
    except WorkflowReviewRepositoryError as error:
        raise HTTPException(status_code=503, detail="Workflow review decision could not be saved") from error
    if updated is None:
        raise HTTPException(status_code=404, detail="Workflow review not found")
    return updated


@router.post("/{review_id}/reject", response_model=WorkflowReviewRead)
def reject_review(review_id: UUID, request: WorkflowReviewDecision, reviews: ReviewDependency) -> WorkflowReview:
    review = reviews.get(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Workflow review not found")
    if review.status != "pending_review":
        raise HTTPException(status_code=409, detail="Only pending reviews can be rejected")
    try:
        updated = reviews.decide(
            review_id,
            status="rejected",
            reviewer_decision="rejected",
            reviewer_note=request.reviewer_note,
        )
    except WorkflowReviewRepositoryError as error:
        raise HTTPException(status_code=503, detail="Workflow review decision could not be saved") from error
    if updated is None:
        raise HTTPException(status_code=404, detail="Workflow review not found")
    return updated
