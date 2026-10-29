from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Document, WorkflowReview
from app.db.repositories import DocumentRepository, WorkflowReviewRepository


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_workflow_review_repository_persists_and_decides_reviews() -> None:
    with make_session() as session:
        documents = DocumentRepository(session)
        reviews = WorkflowReviewRepository(session)
        document = documents.create(
            filename="brief.txt",
            content_type="text/plain",
            size_bytes=10,
            checksum="e" * 64,
            status="indexed",
        )
        result = {"summary": "A grounded summary", "key_points": [], "citations": []}

        review = reviews.create(document_id=document.id, workflow_type="summary", structured_result=result)
        assert review.status == "pending_review"
        assert reviews.list(document_id=document.id)[0].id == review.id

        approved = reviews.decide(
            review.id,
            status="approved",
            reviewer_decision="approved",
            reviewer_note="Checked source",
            structured_result={"summary": "Edited summary", "key_points": [], "citations": []},
        )
        assert approved.status == "approved"
        assert approved.reviewer_decision == "approved"
        assert approved.reviewer_note == "Checked source"
        assert approved.structured_result["summary"] == "Edited summary"
        assert reviews.get(uuid4()) is None


def test_workflow_review_model_is_linked_to_documents() -> None:
    assert {"id", "document_id", "workflow_type", "structured_result", "status", "reviewer_decision", "error_message"}.issubset(
        WorkflowReview.__table__.columns.keys()
    )
