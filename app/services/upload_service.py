from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import tempfile
from typing import Any

from app.db.models import Document
from app.db.repositories import DocumentRepository, DocumentRepositoryError
from app.services.ingestion_service import DocumentIngestionError, DocumentIngestionService


class UploadValidationError(ValueError):
    """Raised when an upload is not an accepted document."""


class DuplicateDocumentError(ValueError):
    def __init__(self, document: Document) -> None:
        super().__init__("A document with identical contents already exists")
        self.document = document


@dataclass(frozen=True)
class UploadResult:
    document: Document
    checksum: str


class DocumentUploadService:
    """Validate an upload, persist metadata, and synchronously ingest it."""

    CONTENT_TYPES = {
        ".pdf": {"application/pdf"},
        ".docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        ".txt": {"text/plain"},
    }

    def __init__(
        self,
        *,
        repository: DocumentRepository,
        ingestion_service: DocumentIngestionService,
        max_upload_size_bytes: int,
    ) -> None:
        self.repository = repository
        self.ingestion_service = ingestion_service
        self.max_upload_size_bytes = max_upload_size_bytes

    def upload(self, *, filename: str, content_type: str | None, content: bytes) -> UploadResult:
        safe_filename = Path(filename).name.strip()
        if not safe_filename:
            raise UploadValidationError("A filename is required")

        extension = Path(safe_filename).suffix.lower()
        if extension not in self.CONTENT_TYPES:
            raise UploadValidationError("Unsupported document format")
        if not content:
            raise UploadValidationError("Uploaded document is empty")
        if len(content) > self.max_upload_size_bytes:
            raise UploadValidationError("Uploaded document exceeds the configured size limit")

        normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
        allowed_types = self.CONTENT_TYPES[extension]
        if normalized_content_type and normalized_content_type not in allowed_types and normalized_content_type != "application/octet-stream":
            raise UploadValidationError("Uploaded content type does not match the file extension")

        checksum = sha256(content).hexdigest()
        existing = self.repository.get_by_checksum(checksum)
        if existing is not None:
            raise DuplicateDocumentError(existing)

        document = self.repository.create(
            filename=safe_filename,
            content_type=normalized_content_type or next(iter(allowed_types)),
            size_bytes=len(content),
            checksum=checksum,
        )

        temporary_path: Path | None = None
        try:
            # Close the file before ingestion so Windows extraction libraries
            # can reopen it without a sharing violation.
            with tempfile.NamedTemporaryFile(mode="wb", suffix=extension, delete=False) as temporary_file:
                temporary_file.write(content)
                temporary_path = Path(temporary_file.name)
            self.ingestion_service.ingest(document.id, temporary_path)
        except DocumentIngestionError:
            raise
        except Exception as error:
            # The ingestion service normally owns failure transitions. This
            # fallback protects the API if a custom implementation fails early.
            self.repository.update_status(document.id, status="failed", error_message="Document ingestion failed")
            raise DocumentIngestionError("Document ingestion failed", document_id=document.id) from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

        refreshed = self.repository.get(document.id)
        return UploadResult(document=refreshed or document, checksum=checksum)
