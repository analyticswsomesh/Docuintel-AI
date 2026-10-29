from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(ge=0)
    checksum: str = Field(min_length=1, max_length=64)


class DocumentStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=32)
    error_message: str | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    checksum: str
    status: str
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None
