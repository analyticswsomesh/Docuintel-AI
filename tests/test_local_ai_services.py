import pytest
import json

from app.services.embedding_service import EmbeddingService, LocalModelUnavailableError
from app.services.ollama_service import OllamaService
from app.services.rag_service import RagService
from app.services.vector_store_service import ChromaVectorStore, RetrievedChunk, TextChunk


class FakeEmbedder:
    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeRetriever:
    def __init__(self, chunks):
        self.chunks = chunks

    def search(self, query, *, document_ids=None):
        return self.chunks


def test_retrieval_service_filters_unexpected_out_of_scope_chunks() -> None:
    class RetrieverVectorStore:
        def query(self, embedding, *, top_k, document_ids=None):
            return [chunk("allowed"), RetrievedChunk("outside", "doc-2", "Other", 0, 0.2)]

    from app.services.vector_store_service import RetrievalService

    results = RetrievalService(FakeEmbedder(), RetrieverVectorStore()).search("question", document_ids=["doc-1"])

    assert [item.id for item in results] == ["allowed"]


class FakeLlm:
    def __init__(self, content):
        self.content = content

    def generate_json(self, **kwargs):
        return {"message": {"content": self.content}}


def chunk(chunk_id="chunk-1"):
    return RetrievedChunk(chunk_id, "doc-1", "The renewal term is twelve months.", 0, 0.1, 4, "agreement.pdf")


def test_embedding_service_checks_local_cache_without_download() -> None:
    calls = []

    def loader(model_name, local_only):
        calls.append((model_name, local_only))
        raise LocalModelUnavailableError("not cached")

    service = EmbeddingService(loader=loader)

    assert service.check_model_available() is False
    assert calls == [("BAAI/bge-small-en-v1.5", True)]


def test_rag_returns_grounded_answer_with_validated_citation() -> None:
    response = '{"answer":"The renewal term is twelve months.","citation_ids":["chunk-1"],"abstain":false}'
    result = RagService(FakeRetriever([chunk()]), FakeLlm(response)).answer("How long is the renewal term?")

    assert result.abstained is False
    assert result.answer.startswith("The renewal term")
    assert result.citations[0].chunk_id == "chunk-1"
    assert result.citations[0].page_number == 4


def test_rag_abstains_when_model_cites_unknown_chunk() -> None:
    response = '{"answer":"It is twelve months.","citation_ids":["not-retrieved"],"abstain":false}'
    result = RagService(FakeRetriever([chunk()]), FakeLlm(response)).answer("What is the term?")

    assert result.abstained is True
    assert result.reason == "invalid_or_missing_citations"
    assert result.citations == []


def test_rag_rejects_document_id_when_chunk_id_is_required() -> None:
    response = '{"answer":"It is twelve months.","citation_ids":["doc-1"],"abstain":false}'
    result = RagService(FakeRetriever([chunk()]), FakeLlm(response)).answer("What is the term?")

    assert result.abstained is True
    assert result.reason == "invalid_or_missing_citations"


def test_rag_accepts_live_shaped_chunk_id_and_preserves_metadata() -> None:
    live_chunk = chunk("bb348b19-aec8-482f-b5a2-d72a512f0899:0")
    response = '{"answer":"The renewal term is twelve months.","citation_ids":["bb348b19-aec8-482f-b5a2-d72a512f0899:0"],"abstain":false}'
    result = RagService(FakeRetriever([live_chunk]), FakeLlm(response)).answer("How long is the renewal term?")

    assert result.abstained is False
    assert result.citations[0].chunk_id == live_chunk.id
    assert result.citations[0].document_id == live_chunk.document_id


def test_rag_abstains_without_retrieved_evidence_and_does_not_call_llm() -> None:
    class FailingLlm:
        def generate_json(self, **kwargs):
            raise AssertionError("LLM must not be called without evidence")

    result = RagService(FakeRetriever([]), FailingLlm()).answer("Unsupported question")

    assert result.abstained is True
    assert result.reason == "no_retrieved_evidence"


def test_ollama_rejects_non_loopback_endpoint() -> None:
    with pytest.raises(ValueError):
        OllamaService(base_url="https://example.com", model="qwen3:4b")


def test_ollama_checks_configured_model_before_generation() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"models":[{"name":"qwen3:4b"}]}'

    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        return Response()

    service = OllamaService(opener=opener)

    assert service.check_model_available() is True
    assert calls[0][0].endswith("/api/tags")


def test_ollama_requests_non_thinking_json_generation() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"models":[{"name":"qwen3:4b"}]}'

    requests = []

    def opener(request, timeout):
        requests.append(request)
        if request.full_url.endswith("/api/tags"):
            return Response()
        response = Response()
        response.read = lambda: b'{"message":{"content":"{\\"answer\\":\\"ok\\",\\"citation_ids\\":[],\\"abstain\\":true}"}}'
        return response

    service = OllamaService(opener=opener)
    service.generate_json(system_prompt="system", user_prompt="question")

    payload = json.loads(requests[-1].data.decode("utf-8"))
    assert payload["think"] is False
    assert payload["format"] == "json"


class FakeCollection:
    def __init__(self):
        self.upsert_args = None
        self.query_args = None
        self.delete_args = None

    def upsert(self, **kwargs):
        self.upsert_args = kwargs

    def query(self, **kwargs):
        self.query_args = kwargs
        return {
            "ids": [["chunk-1"]],
            "documents": [["Relevant passage"]],
            "metadatas": [[{"document_id": "doc-1", "chunk_index": 2, "page_number": 7, "source_name": "file.pdf"}]],
            "distances": [[0.12]],
        }

    def delete(self, **kwargs):
        self.delete_args = kwargs


class FakeChromaClient:
    def __init__(self, collection):
        self.collection = collection

    def get_or_create_collection(self, **kwargs):
        return self.collection


def test_chroma_adapter_preserves_metadata_and_document_scope() -> None:
    collection = FakeCollection()
    store = ChromaVectorStore(client=FakeChromaClient(collection))
    store.upsert([TextChunk("chunk-1", "doc-1", "Relevant passage", 2, 7, "file.pdf")], [[0.1, 0.2]])

    results = store.query([0.1, 0.2], top_k=3, document_ids=["doc-1"])
    store.delete_document("doc-1")

    assert collection.upsert_args["metadatas"] == [{"document_id": "doc-1", "chunk_index": 2, "page_number": 7, "source_name": "file.pdf"}]
    assert collection.query_args["where"] == {"document_id": {"$in": ["doc-1"]}}
    assert results[0].page_number == 7
    assert collection.delete_args == {"where": {"document_id": "doc-1"}}
