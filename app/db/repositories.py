from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Document, WorkflowReview


class DocumentRepositoryError(RuntimeError):
    """Safe application-level wrapper for document persistence failures."""


class DocumentRepository:
    """Persistence operations for authoritative document metadata."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
        checksum: str,
        status: str = "uploaded",
    ) -> Document:
        document = Document(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum=checksum,
            status=status,
        )
        self.session.add(document)
        try:
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            raise DocumentRepositoryError("Could not create document metadata") from error
        self.session.refresh(document)
        return document

    def get(self, document_id: UUID) -> Document | None:
        return self.session.get(Document, document_id)

    def get_by_checksum(self, checksum: str) -> Document | None:
        statement = select(Document).where(Document.checksum == checksum)
        return self.session.scalars(statement).first()

    def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[Document]:
        statement = (
            select(Document)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return self.session.scalars(statement).all()

    def update_status(self, document_id: UUID, *, status: str, error_message: str | None = None) -> Document | None:
        document = self.get(document_id)
        if document is None:
            return None
        document.status = status
        document.error_message = error_message
        try:
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            raise DocumentRepositoryError("Could not update document status") from error
        self.session.refresh(document)
        return document

    def delete(self, document_id: UUID) -> bool:
        document = self.get(document_id)
        if document is None:
            return False
        self.session.delete(document)
        try:
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            raise DocumentRepositoryError("Could not delete document metadata") from error
        return True


class WorkflowReviewRepositoryError(RuntimeError):
    """Safe application-level wrapper for workflow review persistence failures."""


class WorkflowReviewRepository:
    """Persistence operations for human-reviewable workflow results."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        document_id: UUID,
        workflow_type: str,
        structured_result: dict,
        status: str = "pending_review",
        error_message: str | None = None,
    ) -> WorkflowReview:
        review = WorkflowReview(
            document_id=document_id,
            workflow_type=workflow_type,
            structured_result=structured_result,
            status=status,
            error_message=error_message,
        )
        self.session.add(review)
        try:
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            raise WorkflowReviewRepositoryError("Could not create workflow review") from error
        self.session.refresh(review)
        return review

    def get(self, review_id: UUID) -> WorkflowReview | None:
        return self.session.get(WorkflowReview, review_id)

    def list(self, *, document_id: UUID | None = None, limit: int = 50, offset: int = 0) -> Sequence[WorkflowReview]:
        statement = select(WorkflowReview).order_by(WorkflowReview.created_at.desc(), WorkflowReview.id.desc())
        if document_id is not None:
            statement = statement.where(WorkflowReview.document_id == document_id)
        return self.session.scalars(statement.limit(limit).offset(offset)).all()

    def decide(
        self,
        review_id: UUID,
        *,
        status: str,
        reviewer_decision: str,
        reviewer_note: str | None = None,
        structured_result: dict | None = None,
    ) -> WorkflowReview | None:
        review = self.get(review_id)
        if review is None:
            return None
        review.status = status
        review.reviewer_decision = reviewer_decision
        review.reviewer_note = reviewer_note
        if structured_result is not None:
            review.structured_result = structured_result
        try:
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            raise WorkflowReviewRepositoryError("Could not save workflow review decision") from error
        self.session.refresh(review)
        return review
