from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest

from app.db.base import Base
from app.db.models import Document
from app.db.repositories import DocumentRepository, DocumentRepositoryError
from app.db.session import create_database_engine
from app.core.config import Settings


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_document_repository_supports_create_list_update_and_delete() -> None:
    with make_session() as session:
        repository = DocumentRepository(session)
        missing_id = uuid4()
        assert repository.get(missing_id) is None
        assert repository.update_status(missing_id, status="failed") is None
        assert repository.delete(missing_id) is False

        document = repository.create(
            filename="brief.txt",
            content_type="text/plain",
            size_bytes=42,
            checksum="a" * 64,
        )

        assert document.status == "uploaded"
        assert repository.get(document.id).filename == "brief.txt"
        assert [item.id for item in repository.list()] == [document.id]

        updated = repository.update_status(document.id, status="failed", error_message="test failure")
        assert updated.status == "failed"
        assert updated.error_message == "test failure"

        assert repository.delete(document.id) is True
        assert repository.get(document.id) is None
        assert repository.delete(document.id) is False


def test_document_checksum_is_unique() -> None:
    with make_session() as session:
        repository = DocumentRepository(session)
        repository.create(
            filename="one.txt",
            content_type="text/plain",
            size_bytes=1,
            checksum="b" * 64,
        )

        with pytest.raises(DocumentRepositoryError):
            repository.create(
                filename="two.txt",
                content_type="text/plain",
                size_bytes=1,
                checksum="b" * 64,
            )


def test_document_model_has_reference_metadata_fields() -> None:
    assert {"id", "filename", "content_type", "size_bytes", "checksum", "status", "created_at", "error_message"}.issubset(
        Document.__table__.columns.keys()
    )


def test_postgresql_engine_uses_psycopg_driver_without_connecting() -> None:
    engine = create_database_engine(Settings(database_url="postgresql+psycopg://user:pass@localhost/db"))

    assert engine.url.drivername == "postgresql+psycopg"
    engine.dispose()
