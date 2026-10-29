from app.core.config import Settings


def test_settings_have_local_ai_defaults() -> None:
    settings = Settings()

    assert settings.ollama_base_url.startswith("http://127.0.0.1")
    assert settings.ollama_model == "qwen3:4b"
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.max_upload_size_mb == 25
    assert settings.api_base_url == "http://127.0.0.1:8000"
    assert settings.ollama_timeout_seconds == 150.0
    assert settings.api_timeout_seconds == 180.0
    assert settings.api_timeout_seconds > settings.ollama_timeout_seconds


def test_settings_read_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "40")
    monkeypatch.setenv("API_BASE_URL", "http://localhost:9000")
    monkeypatch.setenv("API_TIMEOUT_SECONDS", "120")

    settings = Settings.from_environment()

    assert settings.app_env == "test"
    assert settings.max_upload_size_mb == 40
    assert settings.api_base_url == "http://localhost:9000"
    assert settings.api_timeout_seconds == 120
