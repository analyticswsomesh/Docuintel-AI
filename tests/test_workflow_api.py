from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_document_repository, get_workflow_extraction_service, get_workflow_review_repository
from app.api.schemas.workflows import WorkflowResult
from app.db.base import Base
from app.db.repositories import DocumentRepository, WorkflowReviewRepository
from app.main import app
from app.services.rag_service import Citation, RagAnswer
from app.services.workflow_service import WorkflowExtractionError


class FakeWorkflowService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def extract(self, document_id, workflow_type: str) -> WorkflowResult:
        self.calls.append((str(document_id), workflow_type))
        if self.error:
            raise self.error
        return WorkflowResult(
            summary="The project has a documented deadline.",
            key_points=[],
            citations=[Citation(chunk_id="doc-1:0", document_id=str(document_id), source_name="brief.txt")],
        )


@pytest.fixture
def workflow_context():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    documents = DocumentRepository(session)
    reviews = WorkflowReviewRepository(session)
    workflow = FakeWorkflowService()
    app.dependency_overrides[get_document_repository] = lambda: documents
    app.dependency_overrides[get_workflow_review_repository] = lambda: reviews
    app.dependency_overrides[get_workflow_extraction_service] = lambda: workflow
    with TestClient(app) as client:
        yield client, documents, reviews, workflow
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def make_document(repository: DocumentRepository, *, status: str = "indexed"):
    return repository.create(
        filename="brief.txt",
        content_type="text/plain",
        size_bytes=10,
        checksum=uuid4().hex + uuid4().hex,
        status=status,
    )


def test_review_create_approve_edit_and_invalid_transition(workflow_context) -> None:
    client, documents, reviews, workflow = workflow_context
    document = make_document(documents)

    created = client.post("/api/reviews", json={"document_id": str(document.id), "workflow_type": "summary"})
    assert created.status_code == 201
    review_id = created.json()["id"]
    assert created.json()["status"] == "pending_review"
    assert workflow.calls == [(str(document.id), "summary")]

    listed = client.get("/api/reviews", params={"document_id": str(document.id)})
    detail = client.get(f"/api/reviews/{review_id}")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == review_id
    assert detail.status_code == 200
    assert detail.json()["structured_result"]["citations"][0]["source_name"] == "brief.txt"

    approved = client.post(
        f"/api/reviews/{review_id}/approve",
        json={"edited_summary": "Reviewer-approved summary", "reviewer_note": "Checked evidence"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["structured_result"]["summary"] == "Reviewer-approved summary"
    assert approved.json()["structured_result"]["citations"][0]["chunk_id"] == "doc-1:0"

    again = client.post(f"/api/reviews/{review_id}/approve", json={})
    assert again.status_code == 409
    assert reviews.get(uuid4()) is None


def test_review_reject_persists_and_cannot_be_rejected_twice(workflow_context) -> None:
    client, documents, _, _ = workflow_context
    document = make_document(documents)
    created = client.post("/api/reviews", json={"document_id": str(document.id)})
    review_id = created.json()["id"]

    rejected = client.post(f"/api/reviews/{review_id}/reject", json={"reviewer_note": "Needs correction"})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["reviewer_decision"] == "rejected"

    again = client.post(f"/api/reviews/{review_id}/reject", json={})
    assert again.status_code == 409


def test_review_requires_indexed_document_and_valid_request(workflow_context) -> None:
    client, documents, _, _ = workflow_context
    pending = make_document(documents, status="uploaded")
    missing = client.post("/api/reviews", json={"document_id": str(uuid4())})
    unindexed = client.post("/api/reviews", json={"document_id": str(pending.id)})
    malformed = client.post("/api/reviews", json={"document_id": str(pending.id), "workflow_type": "action_items"})

    assert missing.status_code == 404
    assert unindexed.status_code == 409
    assert malformed.status_code == 422


def test_review_extraction_failure_is_persisted_as_failed(workflow_context) -> None:
    client, documents, reviews, _ = workflow_context
    document = make_document(documents)
    failing = FakeWorkflowService(error=WorkflowExtractionError("missing validated evidence"))
    app.dependency_overrides[get_workflow_extraction_service] = lambda: failing

    response = client.post("/api/reviews", json={"document_id": str(document.id)})

    assert response.status_code == 422
    failed_id = response.json()["detail"]["review_id"]
    failed = reviews.get(UUID(failed_id))
    assert failed.status == "failed"
    assert failed.error_message == "missing validated evidence"
