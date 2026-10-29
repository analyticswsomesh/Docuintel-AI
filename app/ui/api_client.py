from typing import Any

import httpx


class APIClientError(RuntimeError):
    """A safe, user-facing error from the FastAPI client."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class DocumentAPIClient:
    def __init__(self, base_url: str, *, timeout: float = 90.0, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)

    def list_documents(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/documents", params={"limit": limit, "offset": offset})
        return list(payload)

    def get_document(self, document_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/api/documents/{document_id}"))

    def upload_document(self, *, filename: str, content: bytes, content_type: str | None) -> dict[str, Any]:
        return dict(
            self._request(
                "POST",
                "/api/documents",
                files={"file": (filename, content, content_type or "application/octet-stream")},
            )
        )

    def delete_document(self, document_id: str) -> None:
        self._request("DELETE", f"/api/documents/{document_id}")

    def ask_question(self, *, question: str, document_ids: list[str]) -> dict[str, Any]:
        return dict(
            self._request(
                "POST",
                "/api/research/answer",
                json={"question": question, "document_ids": document_ids},
            )
        )

    def list_reviews(self, *, document_id: str | None = None, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if document_id:
            params["document_id"] = document_id
        return list(self._request("GET", "/api/reviews", params=params))

    def get_review(self, review_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/api/reviews/{review_id}"))

    def create_review(self, *, document_id: str, workflow_type: str = "summary") -> dict[str, Any]:
        return dict(self._request("POST", "/api/reviews", json={"document_id": document_id, "workflow_type": workflow_type}))

    def approve_review(self, review_id: str, *, reviewer_note: str | None = None, edited_summary: str | None = None, edited_key_points: list[str] | None = None) -> dict[str, Any]:
        return dict(self._request("POST", f"/api/reviews/{review_id}/approve", json={"reviewer_note": reviewer_note, "edited_summary": edited_summary, "edited_key_points": edited_key_points}))

    def reject_review(self, review_id: str, *, reviewer_note: str | None = None) -> dict[str, Any]:
        return dict(self._request("POST", f"/api/reviews/{review_id}/reject", json={"reviewer_note": reviewer_note}))

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, f"{self.base_url}{path}", **kwargs)
        except httpx.HTTPError as error:
            raise APIClientError("The DocuIntel API is unavailable. Check that the backend is running.") from error
        if response.is_error:
            detail: Any = None
            try:
                detail = response.json().get("detail")
            except ValueError:
                pass
            if isinstance(detail, dict):
                detail = detail.get("message") or detail.get("detail")
            message = str(detail or f"The API returned HTTP {response.status_code}.")
            raise APIClientError(message, status_code=response.status_code)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()
