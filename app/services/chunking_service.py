from collections.abc import Iterable

from app.services.extraction_service import ExtractedPage
from app.services.vector_store_service import TextChunk


class ChunkingError(ValueError):
    """Raised for invalid chunking configuration or empty extracted text."""


class TextChunkingService:
    def __init__(self, chunk_size_chars: int = 1000, chunk_overlap_chars: int = 150) -> None:
        if chunk_size_chars <= 0:
            raise ValueError("chunk_size_chars must be positive")
        if chunk_overlap_chars < 0 or chunk_overlap_chars >= chunk_size_chars:
            raise ValueError("chunk_overlap_chars must be non-negative and smaller than chunk_size_chars")
        self.chunk_size_chars = chunk_size_chars
        self.chunk_overlap_chars = chunk_overlap_chars

    def create_chunks(
        self,
        pages: Iterable[ExtractedPage],
        *,
        document_id: str,
        source_name: str,
    ) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        for page in pages:
            text = " ".join(page.text.split())
            if not text:
                continue
            start = 0
            while start < len(text):
                end = min(start + self.chunk_size_chars, len(text))
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunk_index = len(chunks)
                    chunks.append(
                        TextChunk(
                            id=f"{document_id}:{chunk_index}",
                            document_id=document_id,
                            text=chunk_text,
                            chunk_index=chunk_index,
                            page_number=page.page_number,
                            source_name=source_name,
                        )
                    )
                if end >= len(text):
                    break
                start = end - self.chunk_overlap_chars
        if not chunks:
            raise ChunkingError("Document contains no extractable text")
        return chunks
