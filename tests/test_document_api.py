from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_document_repository, get_ingestion_service, get_vector_store
from app.core.config import Settings
from app.db.base import Base
from app.db.repositories import DocumentRepository
from app.main import app
from app.services.ingestion_service import DocumentIngestionError, DocumentStatus
from app.services.chunking_service import TextChunkingService
from app.services.extraction_service import DocumentExtractionService
from app.services.ingestion_service import DocumentIngestionService
from app.services.upload_service import DocumentUploadService


class FakeIngestionService:
    def __init__(self, repository: DocumentRepository, *, fail: bool = False) -> None:
        self.repository = repository
        self.fail = fail
        self.paths: list[Path] = []

    def ingest(self, document_id: UUID, file_path: str) -> None:
        self.paths.append(Path(file_path))
        if self.fail:
            self.repository.update_status(document_id, status=DocumentStatus.FAILED.value, error_message="test processing failure")
            raise DocumentIngestionError("Document ingestion failed", document_id=document_id)
        self.repository.update_status(document_id, status=DocumentStatus.INDEXED.value)


class FakeVectorStore:
    def __init__(self, *, fail: bool = False) -> None:
        self.deleted: list[str] = []
        self.fail = fail

    def delete_document(self, document_id: str) -> None:
        if self.fail:
            raise RuntimeError("vector cleanup failed")
        self.deleted.append(document_id)


class PipelineEmbedding:
    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class PipelineVectorStore:
    def __init__(self) -> None:
        self.chunks = []

    def delete_document(self, document_id: str) -> None:
        self.chunks = [chunk for chunk in self.chunks if chunk.document_id != document_id]

    def upsert(self, chunks, embeddings) -> None:
        self.chunks.extend(chunks)


@pytest.fixture
def api_context(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    repository = DocumentRepository(session)
    ingestion = FakeIngestionService(repository)
    vector_store = FakeVectorStore()
    monkeypatch.setattr("app.api.routes.documents.get_settings", lambda: Settings(max_upload_size_mb=1))
    app.dependency_overrides[get_document_repository] = lambda: repository
    app.dependency_overrides[get_ingestion_service] = lambda: ingestion
    app.dependency_overrides[get_vector_store] = lambda: vector_store
    with TestClient(app) as client:
        yield client, repository, ingestion, vector_store
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_uploads_supported_text_and_cleans_temporary_file(api_context) -> None:
    client, repository, ingestion, _ = api_context

    response = client.post(
        "/api/documents",
        files={"file": ("notes.txt", b"Project evidence", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["status"] == "indexed"
    assert repository.get(UUID(body["id"])) is not None
    assert ingestion.paths and not ingestion.paths[0].exists()


def test_real_txt_upload_reaches_extractor_after_temp_file_is_closed() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    repository = DocumentRepository(session)
    vector_store = PipelineVectorStore()
    ingestion = DocumentIngestionService(
        repository=repository,
        extractor=DocumentExtractionService(),
        chunker=TextChunkingService(chunk_size_chars=100, chunk_overlap_chars=10),
        embedding_service=PipelineEmbedding(),
        vector_store=vector_store,
        max_upload_size_bytes=1024 * 1024,
    )

    try:
        result = DocumentUploadService(
            repository=repository,
            ingestion_service=ingestion,
            max_upload_size_bytes=1024 * 1024,
        ).upload(filename="real.txt", content_type="text/plain", content=b"Text extraction works.")

        assert result.document.status == DocumentStatus.INDEXED.value
        assert vector_store.chunks[0].text == "Text extraction works."
    finally:
        session.close()
        engine.dispose()


def test_rejects_unsupported_and_empty_uploads(api_context) -> None:
    client, repository, _, _ = api_context

    unsupported = client.post("/api/documents", files={"file": ("data.csv", b"a,b", "text/csv")})
    empty = client.post("/api/documents", files={"file": ("empty.txt", b"", "text/plain")})

    assert unsupported.status_code == 415
    assert empty.status_code == 400
    assert repository.list() == []


def test_duplicate_checksum_does_not_create_second_metadata_row(api_context) -> None:
    client, repository, _, _ = api_context
    upload = {"file": ("notes.txt", b"same contents", "text/plain")}

    first = client.post("/api/documents", files=upload)
    second = client.post("/api/documents", files=upload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"]["document_id"] == first.json()["id"]
    assert len(repository.list()) == 1


def test_rejects_oversized_upload(api_context) -> None:
    client, repository, _, _ = api_context

    response = client.post(
        "/api/documents",
        files={"file": ("large.txt", b"x" * (1024 * 1024 + 1), "text/plain")},
    )

    assert response.status_code == 413
    assert repository.list() == []


def test_lists_gets_and_validates_document_ids(api_context) -> None:
    client, repository, _, _ = api_context
    first = repository.create(filename="one.txt", content_type="text/plain", size_bytes=1, checksum="1" * 64)
    repository.create(filename="two.txt", content_type="text/plain", size_bytes=1, checksum="2" * 64)

    listed = client.get("/api/documents?limit=1&offset=0")
    detail = client.get(f"/api/documents/{first.id}")
    missing = client.get("/api/documents/00000000-0000-0000-0000-000000000000")
    invalid = client.get("/api/documents/not-a-uuid")

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert detail.status_code == 200
    assert detail.json()["id"] == str(first.id)
    assert missing.status_code == 404
    assert invalid.status_code == 422


def test_deletes_vectors_before_metadata_and_handles_missing_ids(api_context) -> None:
    client, repository, _, vector_store = api_context
    document = repository.create(filename="remove.txt", content_type="text/plain", size_bytes=1, checksum="3" * 64)

    response = client.delete(f"/api/documents/{document.id}")
    missing = client.delete(f"/api/documents/{document.id}")

    assert response.status_code == 204
    assert vector_store.deleted == [str(document.id)]
    assert repository.get(document.id) is None
    assert missing.status_code == 404


def test_delete_keeps_metadata_when_vector_cleanup_fails(api_context) -> None:
    client, repository, _, vector_store = api_context
    vector_store.fail = True
    document = repository.create(filename="keep.txt", content_type="text/plain", size_bytes=1, checksum="4" * 64)

    response = client.delete(f"/api/documents/{document.id}")

    assert response.status_code == 503
    assert repository.get(document.id) is not None


def test_upload_failure_returns_failed_status_and_document_id(api_context) -> None:
    client, repository, _, _ = api_context
    failing_ingestion = FakeIngestionService(repository, fail=True)
    app.dependency_overrides[get_ingestion_service] = lambda: failing_ingestion

    response = client.post(
        "/api/documents",
        files={"file": ("broken.txt", b"content", "text/plain")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["status"] == "failed"
    failed = repository.list()[0]
    assert detail["document_id"] == str(failed.id)
    assert failed.status == "failed"
