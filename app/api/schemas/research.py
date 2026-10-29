from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.services.rag_service import Citation


class ResearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[UUID] = Field(min_length=1, max_length=50)

    @field_validator("question")
    @classmethod
    def question_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must contain text")
        return value.strip()


class ResearchResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    abstained: bool
    reason: str | None = None
