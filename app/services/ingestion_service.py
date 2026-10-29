from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from app.db.repositories import DocumentRepository
from app.services.chunking_service import TextChunkingService
from app.services.extraction_service import DocumentExtractionService


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentIngestionError(RuntimeError):
    """Raised when document processing fails after status cleanup."""

    def __init__(self, message: str, *, document_id: UUID | None = None) -> None:
        super().__init__(message)
        self.document_id = document_id


class DocumentNotFoundError(DocumentIngestionError):
    """Raised when ingestion is requested for an unknown document record."""


class DocumentIngestionService:
    def __init__(
        self,
        *,
        repository: DocumentRepository,
        extractor: DocumentExtractionService,
        chunker: TextChunkingService,
        embedding_service: Any,
        vector_store: Any,
        max_upload_size_bytes: int,
    ) -> None:
        self.repository = repository
        self.extractor = extractor
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.max_upload_size_bytes = max_upload_size_bytes

    def ingest(self, document_id: UUID, file_path: str | Path):
        document = self.repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError("Document metadata was not found")

        self.repository.update_status(document_id, status=DocumentStatus.PROCESSING.value, error_message=None)
        document_key = str(document_id)
        try:
            # Reprocessing starts from a clean vector state, even when local
            # file validation fails before extraction can begin.
            self.vector_store.delete_document(document_key)
            path = Path(file_path)
            if not path.is_file():
                raise ValueError("Document file does not exist")
            if path.stat().st_size > self.max_upload_size_bytes:
                raise ValueError("Document exceeds the configured upload size limit")

            pages = self.extractor.extract(path, filename=document.filename, content_type=document.content_type)
            chunks = self.chunker.create_chunks(pages, document_id=document_key, source_name=document.filename)
            embeddings = self.embedding_service.embed([chunk.text for chunk in chunks])
            self.vector_store.upsert(chunks, embeddings)
        except Exception as error:
            self._clear_vectors(document_key)
            message = str(error).strip()[:500] or type(error).__name__
            self.repository.update_status(document_id, status=DocumentStatus.FAILED.value, error_message=message)
            raise DocumentIngestionError("Document ingestion failed", document_id=document_id) from error

        return self.repository.update_status(document_id, status=DocumentStatus.INDEXED.value, error_message=None)

    def _clear_vectors(self, document_id: str) -> None:
        try:
            self.vector_store.delete_document(document_id)
        except Exception:
            # The document remains failed; cleanup errors must not mask that state.
            pass
