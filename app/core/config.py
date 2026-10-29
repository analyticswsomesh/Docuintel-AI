from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    app_name: str = "DocuIntel AI"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_base_url: str = "http://127.0.0.1:8000"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://docuintel:change-me@localhost:5432/docuintel"
    chroma_path: str = "./data/chroma"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    rag_top_k: int = Field(default=5, ge=1, le=20)
    ollama_timeout_seconds: float = Field(default=150.0, gt=0, le=300)
    api_timeout_seconds: float = Field(default=180.0, gt=0, le=300)
    max_upload_size_mb: int = Field(default=25, ge=1, le=500)
    chunk_size_chars: int = Field(default=1000, ge=100, le=10000)
    chunk_overlap_chars: int = Field(default=150, ge=0, le=2000)

    @classmethod
    def from_environment(cls) -> "Settings":
        values: dict[str, object] = {}
        mapping = {
            "APP_NAME": "app_name", "APP_ENV": "app_env", "API_HOST": "api_host",
            "API_PORT": "api_port", "API_BASE_URL": "api_base_url", "LOG_LEVEL": "log_level", "DATABASE_URL": "database_url",
            "CHROMA_PATH": "chroma_path", "OLLAMA_BASE_URL": "ollama_base_url",
            "OLLAMA_MODEL": "ollama_model", "EMBEDDING_MODEL": "embedding_model",
            "RAG_TOP_K": "rag_top_k", "OLLAMA_TIMEOUT_SECONDS": "ollama_timeout_seconds",
            "API_TIMEOUT_SECONDS": "api_timeout_seconds",
            "MAX_UPLOAD_SIZE_MB": "max_upload_size_mb", "CHUNK_SIZE_CHARS": "chunk_size_chars",
            "CHUNK_OVERLAP_CHARS": "chunk_overlap_chars",
        }
        for env_name, field_name in mapping.items():
            if (value := os.getenv(env_name)) is not None:
                values[field_name] = value
        return cls(**values)


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
