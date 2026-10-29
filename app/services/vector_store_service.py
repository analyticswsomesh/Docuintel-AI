from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TextChunk:
    id: str
    document_id: str
    text: str
    chunk_index: int
    page_number: int | None = None
    source_name: str | None = None

    def metadata(self) -> dict[str, Any]:
        values: dict[str, Any] = {
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
        }
        if self.page_number is not None:
            values["page_number"] = self.page_number
        if self.source_name is not None:
            values["source_name"] = self.source_name
        return values


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    document_id: str
    text: str
    chunk_index: int
    distance: float
    page_number: int | None = None
    source_name: str | None = None


class ChromaVectorStore:
    """Persistent ChromaDB adapter; the dependency is imported only when used."""

    def __init__(self, persist_path: str = "./data/chroma", collection_name: str = "document_chunks", client: Any | None = None) -> None:
        self.persist_path = Path(persist_path)
        self.collection_name = collection_name
        self._client = client
        self._collection: Any | None = None

    def _get_collection(self) -> Any:
        if self._collection is not None:
            return self._collection
        if self._client is None:
            try:
                import chromadb
            except ImportError as error:
                raise RuntimeError("chromadb is not installed; install project dependencies before using retrieval.") from error
            self.persist_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.persist_path))
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def upsert(self, chunks: list[TextChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return
        self._get_collection().upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[chunk.metadata() for chunk in chunks],
        )

    def query(self, embedding: list[float], *, top_k: int = 5, document_ids: list[str] | None = None) -> list[RetrievedChunk]:
        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}}
        result = self._get_collection().query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            RetrievedChunk(
                id=chunk_id,
                document_id=str(metadata["document_id"]),
                text=document,
                chunk_index=int(metadata["chunk_index"]),
                distance=float(distance),
                page_number=int(metadata["page_number"]) if metadata.get("page_number") is not None else None,
                source_name=str(metadata["source_name"]) if metadata.get("source_name") is not None else None,
            )
            for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances)
        ]

    def delete_document(self, document_id: str) -> None:
        self._get_collection().delete(where={"document_id": document_id})


class RetrievalService:
    def __init__(self, embedding_service: Any, vector_store: ChromaVectorStore, top_k: int = 5) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.top_k = top_k

    def search(self, query: str, *, document_ids: list[str] | None = None, top_k: int | None = None) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        query_embedding = self.embedding_service.embed([query])[0]
        results = self.vector_store.query(query_embedding, top_k=top_k or self.top_k, document_ids=document_ids)
        if document_ids is None:
            return results
        allowed_document_ids = set(document_ids)
        return [chunk for chunk in results if chunk.document_id in allowed_document_ids]
