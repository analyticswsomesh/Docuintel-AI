import httpx

from app.ui.api_client import APIClientError, DocumentAPIClient


def test_document_api_client_covers_library_operations() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET" and request.url.path == "/api/documents":
            return httpx.Response(200, json=[{"id": "doc-1", "filename": "brief.txt", "status": "indexed"}])
        if request.method == "GET" and request.url.path == "/api/documents/doc-1":
            return httpx.Response(200, json={"id": "doc-1", "filename": "brief.txt", "status": "indexed"})
        if request.method == "POST" and request.url.path == "/api/documents":
            assert b"brief.txt" in request.read()
            return httpx.Response(201, json={"id": "doc-1", "filename": "brief.txt", "status": "indexed"})
        if request.method == "DELETE" and request.url.path == "/api/documents/doc-1":
            return httpx.Response(204)
        if request.method == "POST" and request.url.path == "/api/research/answer":
            return httpx.Response(200, json={"answer": "Grounded answer", "citations": [], "abstained": False, "reason": None})
        return httpx.Response(404, json={"detail": "not found"})

    client = DocumentAPIClient("http://api.test", client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.list_documents() == [{"id": "doc-1", "filename": "brief.txt", "status": "indexed"}]
    assert client.get_document("doc-1")["status"] == "indexed"
    assert client.upload_document(filename="brief.txt", content=b"evidence", content_type="text/plain")["id"] == "doc-1"
    assert client.delete_document("doc-1") is None
    assert client.ask_question(question="What is relevant?", document_ids=["doc-1"])["answer"] == "Grounded answer"
    assert [request.method for request in requests] == ["GET", "GET", "POST", "DELETE", "POST"]


def test_document_api_client_surfaces_safe_api_errors() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"detail": "Documents could not be loaded"}))
    client = DocumentAPIClient("http://api.test", client=httpx.Client(transport=transport))

    try:
        client.list_documents()
    except APIClientError as error:
        assert str(error) == "Documents could not be loaded"
        assert error.status_code == 503
    else:
        raise AssertionError("APIClientError was not raised")


def test_document_api_client_covers_review_operations() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET" and request.url.path == "/api/reviews":
            return httpx.Response(200, json=[{"id": "review-1", "status": "pending_review"}])
        if request.method == "GET" and request.url.path == "/api/reviews/review-1":
            return httpx.Response(200, json={"id": "review-1", "status": "pending_review"})
        if request.method == "POST" and request.url.path == "/api/reviews":
            return httpx.Response(201, json={"id": "review-1", "status": "pending_review"})
        if request.method == "POST" and request.url.path.endswith("/approve"):
            return httpx.Response(200, json={"id": "review-1", "status": "approved"})
        if request.method == "POST" and request.url.path.endswith("/reject"):
            return httpx.Response(200, json={"id": "review-1", "status": "rejected"})
        return httpx.Response(404, json={"detail": "not found"})

    client = DocumentAPIClient("http://api.test", client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.list_reviews(document_id="doc-1")[0]["id"] == "review-1"
    assert client.get_review("review-1")["status"] == "pending_review"
    assert client.create_review(document_id="doc-1")["id"] == "review-1"
    assert client.approve_review("review-1", reviewer_note="checked", edited_summary="Updated")["status"] == "approved"
    assert client.reject_review("review-1", reviewer_note="needs correction")["status"] == "rejected"
    assert [request.method for request in requests] == ["GET", "GET", "POST", "POST", "POST"]
