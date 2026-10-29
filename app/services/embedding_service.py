from collections.abc import Callable, Sequence
from typing import Any


class LocalModelUnavailableError(RuntimeError):
    """Raised when a required local embedding model is not available."""


ModelLoader = Callable[[str, bool], Any]


class EmbeddingService:
    """Lazy local BGE embedding service with download-safe defaults."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", loader: ModelLoader | None = None) -> None:
        self.model_name = model_name
        self._loader = loader or self._load_sentence_transformer
        self._model: Any | None = None

    @staticmethod
    def _load_sentence_transformer(model_name: str, local_only: bool) -> Any:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise LocalModelUnavailableError(
                "sentence-transformers is not installed; install the project dependencies before using embeddings."
            ) from error
        try:
            return SentenceTransformer(model_name, local_files_only=local_only)
        except Exception as error:
            mode = "locally" if local_only else "after an explicit download request"
            raise LocalModelUnavailableError(
                f"Embedding model {model_name!r} is not available {mode}. "
                "Download and verify the exact model artifact before enabling inference."
            ) from error

    def check_model_available(self) -> bool:
        """Check the local cache without downloading or contacting a model host."""
        if self._model is not None:
            return True
        try:
            self._model = self._loader(self.model_name, True)
        except LocalModelUnavailableError:
            return False
        return True

    def load(self, *, allow_download: bool = False) -> Any:
        """Load the model; downloads are opt-in and never used by default."""
        if self._model is None:
            self._model = self._loader(self.model_name, not allow_download)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self.load()
        vectors = model.encode(list(texts), normalize_embeddings=True)
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]
