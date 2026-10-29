from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_document_repository, get_rag_service
from app.api.schemas.research import ResearchRequest, ResearchResponse
from app.db.repositories import DocumentRepository
from app.services.rag_service import RagService


router = APIRouter(prefix="/api/research", tags=["research"])
RepositoryDependency = Annotated[DocumentRepository, Depends(get_document_repository)]
RagDependency = Annotated[RagService, Depends(get_rag_service)]


@router.post("/answer", response_model=ResearchResponse)
def answer_question(request: ResearchRequest, repository: RepositoryDependency, rag_service: RagDependency) -> ResearchResponse:
    selected_ids = list(dict.fromkeys(request.document_ids))
    documents = [repository.get(document_id) for document_id in selected_ids]
    if any(document is None for document in documents):
        raise HTTPException(status_code=404, detail="One or more selected documents were not found")
    if any(document.status != "indexed" for document in documents if document is not None):
        raise HTTPException(status_code=409, detail="All selected documents must be indexed before research")

    try:
        result = rag_service.answer(request.question.strip(), document_ids=[str(document_id) for document_id in selected_ids])
    except Exception as error:
        raise HTTPException(status_code=503, detail="The local research service is unavailable") from error
    return ResearchResponse.model_validate(result.model_dump())
