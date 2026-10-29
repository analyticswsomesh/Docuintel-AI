from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.dependencies import get_document_repository, get_ingestion_service, get_vector_store
from app.api.schemas.documents import DocumentRead
from app.core.config import get_settings
from app.db.models import Document
from app.db.repositories import DocumentRepository, DocumentRepositoryError
from app.services.ingestion_service import DocumentIngestionError, DocumentIngestionService
from app.services.upload_service import DocumentUploadService, DuplicateDocumentError, UploadValidationError
from app.services.vector_store_service import ChromaVectorStore


router = APIRouter(prefix="/api/documents", tags=["documents"])
RepositoryDependency = Annotated[DocumentRepository, Depends(get_document_repository)]
IngestionDependency = Annotated[DocumentIngestionService, Depends(get_ingestion_service)]
VectorStoreDependency = Annotated[ChromaVectorStore, Depends(get_vector_store)]


def get_upload_service(repository: RepositoryDependency, ingestion_service: IngestionDependency) -> DocumentUploadService:
    return DocumentUploadService(
        repository=repository,
        ingestion_service=ingestion_service,
        max_upload_size_bytes=get_settings().max_upload_size_mb * 1024 * 1024,
    )


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    upload_service: Annotated[DocumentUploadService, Depends(get_upload_service)],
) -> Document:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")
    try:
        content = await file.read(upload_service.max_upload_size_bytes + 1)
        return upload_service.upload(filename=file.filename, content_type=file.content_type, content=content).document
    except UploadValidationError as error:
        detail = str(error)
        code = 413 if "size limit" in detail else 415 if "format" in detail or "content type" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from error
    except DuplicateDocumentError as error:
        raise HTTPException(status_code=409, detail={"message": str(error), "document_id": str(error.document.id)}) from error
    except DocumentIngestionError as error:
        document_id = getattr(error, "document_id", None)
        raise HTTPException(
            status_code=422,
            detail={"message": "Document processing failed", "document_id": str(document_id) if document_id else None, "status": "failed"},
        ) from error
    except DocumentRepositoryError as error:
        raise HTTPException(status_code=503, detail="Document metadata could not be stored") from error
    finally:
        await file.close()


@router.get("", response_model=list[DocumentRead])
def list_documents(
    repository: RepositoryDependency,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Document]:
    try:
        return list(repository.list(limit=limit, offset=offset))
    except DocumentRepositoryError as error:
        raise HTTPException(status_code=503, detail="Documents could not be loaded") from error


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: UUID, repository: RepositoryDependency) -> Document:
    document = repository.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, repository: RepositoryDependency, vector_store: VectorStoreDependency) -> None:
    document = repository.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        vector_store.delete_document(str(document_id))
        if not repository.delete(document_id):
            raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Document data could not be deleted safely") from error
