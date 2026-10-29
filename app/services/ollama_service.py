import json
from collections.abc import Callable
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class OllamaUnavailableError(RuntimeError):
    """Raised when local Ollama or the configured model is unavailable."""


UrlOpen = Callable[..., object]


class OllamaService:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "qwen3:4b", timeout_seconds: float = 60.0, opener: UrlOpen | None = None) -> None:
        parsed = urlparse(base_url)
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Ollama must use a loopback URL; hosted inference is not supported")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._open = opener or urlopen

    def _request(self, path: str, *, method: str = "GET", payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(f"{self.base_url}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with self._open(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as error:
            raise OllamaUnavailableError(f"Local Ollama is unavailable at {self.base_url}") from error

    def available_models(self) -> list[str]:
        payload = self._request("/api/tags")
        return [str(item.get("name")) for item in payload.get("models", []) if item.get("name")]

    def check_model_available(self) -> bool:
        try:
            return self.model in self.available_models()
        except OllamaUnavailableError:
            return False

    def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict:
        if not self.check_model_available():
            raise OllamaUnavailableError(f"Configured Ollama model {self.model!r} is not available locally")
        return self._request(
            "/api/chat",
            method="POST",
            payload={
                "model": self.model,
                "stream": False,
                "format": "json",
                "think": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
