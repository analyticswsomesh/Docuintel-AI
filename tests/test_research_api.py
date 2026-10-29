from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_document_repository, get_rag_service
from app.db.base import Base
from app.db.repositories import DocumentRepository
from app.main import app
from app.services.rag_service import Citation, RagAnswer


class FakeRagService:
    def __init__(self, result: RagAnswer | None = None, *, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[str, list[str] | None]] = []

    def answer(self, question: str, *, document_ids: list[str] | None = None) -> RagAnswer:
        self.calls.append((question, document_ids))
        if self.error:
            raise self.error
        return self.result or RagAnswer(answer="", citations=[], abstained=True, reason="no_retrieved_evidence")


@pytest.fixture
def research_context():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    repository = DocumentRepository(session)
    rag = FakeRagService(
        RagAnswer(
            answer="The term is twelve months.",
            citations=[Citation(chunk_id="doc-1:0", document_id="doc-1", page_number=2, source_name="agreement.pdf")],
            abstained=False,
        )
    )
    app.dependency_overrides[get_document_repository] = lambda: repository
    app.dependency_overrides[get_rag_service] = lambda: rag
    with TestClient(app) as client:
        yield client, repository, rag
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_research_endpoint_returns_grounded_response_and_scope(research_context) -> None:
    client, repository, rag = research_context
    document = repository.create(filename="agreement.pdf", content_type="application/pdf", size_bytes=10, checksum="a" * 64, status="indexed")

    response = client.post("/api/research/answer", json={"question": "What is the term?", "document_ids": [str(document.id)]})

    assert response.status_code == 200
    assert response.json()["answer"] == "The term is twelve months."
    assert response.json()["citations"][0]["page_number"] == 2
    assert rag.calls == [("What is the term?", [str(document.id)])]


def test_research_rejects_missing_or_unindexed_documents(research_context) -> None:
    client, repository, _ = research_context
    missing_id = "00000000-0000-0000-0000-000000000000"
    unindexed = repository.create(filename="pending.txt", content_type="text/plain", size_bytes=1, checksum="b" * 64)

    missing = client.post("/api/research/answer", json={"question": "Question", "document_ids": [missing_id]})
    pending = client.post("/api/research/answer", json={"question": "Question", "document_ids": [str(unindexed.id)]})

    assert missing.status_code == 404
    assert pending.status_code == 409


def test_research_rejects_malformed_request(research_context) -> None:
    client, _, _ = research_context

    empty_question = client.post("/api/research/answer", json={"question": "", "document_ids": []})
    invalid_id = client.post("/api/research/answer", json={"question": "Question", "document_ids": ["not-a-uuid"]})

    assert empty_question.status_code == 422
    assert invalid_id.status_code == 422


def test_research_returns_explicit_abstention_when_retrieval_is_empty(research_context) -> None:
    client, repository, _ = research_context
    document = repository.create(filename="notes.txt", content_type="text/plain", size_bytes=1, checksum="c" * 64, status="indexed")
    app.dependency_overrides[get_rag_service] = lambda: FakeRagService()

    response = client.post("/api/research/answer", json={"question": "Unsupported question", "document_ids": [str(document.id)]})

    assert response.status_code == 200
    assert response.json()["abstained"] is True
    assert response.json()["citations"] == []


def test_research_hides_model_failures_as_service_errors(research_context) -> None:
    client, repository, _ = research_context
    document = repository.create(filename="notes.txt", content_type="text/plain", size_bytes=1, checksum="d" * 64, status="indexed")
    app.dependency_overrides[get_rag_service] = lambda: FakeRagService(error=RuntimeError("private model detail"))

    response = client.post("/api/research/answer", json={"question": "Question", "document_ids": [str(document.id)]})

    assert response.status_code == 503
    assert response.json()["detail"] == "The local research service is unavailable"
