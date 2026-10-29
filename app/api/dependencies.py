from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.repositories import DocumentRepository, WorkflowReviewRepository
from app.db.session import get_db_session
from app.services.chunking_service import TextChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.extraction_service import DocumentExtractionService
from app.services.ingestion_service import DocumentIngestionService
from app.services.ollama_service import OllamaService
from app.services.rag_service import RagService
from app.services.vector_store_service import ChromaVectorStore
from app.services.vector_store_service import RetrievalService
from app.services.workflow_service import WorkflowExtractionService


def get_document_repository(session: Session = Depends(get_db_session)) -> DocumentRepository:
    return DocumentRepository(session)


def get_workflow_review_repository(session: Session = Depends(get_db_session)) -> WorkflowReviewRepository:
    return WorkflowReviewRepository(session)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    return EmbeddingService(model_name=settings.embedding_model)


@lru_cache
def get_vector_store() -> ChromaVectorStore:
    return ChromaVectorStore(persist_path=get_settings().chroma_path)


def get_ingestion_service(
    repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentIngestionService:
    settings = get_settings()
    return DocumentIngestionService(
        repository=repository,
        extractor=DocumentExtractionService(),
        chunker=TextChunkingService(settings.chunk_size_chars, settings.chunk_overlap_chars),
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
        max_upload_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
    )


@lru_cache
def get_retrieval_service() -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
        top_k=settings.rag_top_k,
    )


@lru_cache
def get_rag_service() -> RagService:
    settings = get_settings()
    return RagService(
        retrieval_service=get_retrieval_service(),
        llm_service=OllamaService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
        ),
    )


def get_workflow_extraction_service(rag_service: RagService = Depends(get_rag_service)) -> WorkflowExtractionService:
    return WorkflowExtractionService(rag_service)
