# DocuIntel AI

DocuIntel AI is a local-first document intelligence workspace for uploading documents, indexing their contents, asking evidence-grounded questions, and reviewing AI-generated workflow results before approval.

The MVP uses synchronous processing and local AI services. It does not use hosted LLM APIs, hosted embeddings, Celery, Redis, or background workers.

## What is implemented

- PDF, DOCX, and UTF-8 TXT extraction and bounded overlapping chunking.
- PostgreSQL document and workflow metadata with additive Alembic migrations.
- Persistent ChromaDB retrieval with document-scoped searches and cleanup.
- Local BAAI/bge-small-en-v1.5 embeddings when the model is already available locally.
- Local Ollama/Qwen3 research answers with citation validation and explicit abstention.
- FastAPI document, research, and workflow-review APIs.
- Streamlit workspace with Overview, Documents, Research, and Reviews pages.
- Human confirmation before workflow approval or rejection.

## Architecture

```text
docuintelAI/
├── app/
│   ├── api/
│   │   ├── routes/       # FastAPI document, research, and workflow endpoints
│   │   └── schemas/      # Pydantic request/response models
│   ├── core/             # Environment-backed settings
│   ├── db/               # SQLAlchemy models, sessions, and repositories
│   ├── services/         # Extraction, chunking, ingestion, embeddings,
│   │                      # ChromaDB, Ollama, RAG, upload, and workflow logic
│   ├── ui/               # Streamlit app, API client, and reusable UI components
│   └── main.py           # FastAPI application entry point
├── migrations/           # Alembic environment and additive schema revisions
├── tests/                # Unit, API, ingestion, RAG, repository, and UI-client tests
├── docs/                 # Technical reference and project documentation
├── data/                 # Local runtime storage; ignored by Git
├── .env.example          # Safe configuration template
├── AGENTS.md             # Project conventions and constraints
├── alembic.ini           # Migration configuration
└── pyproject.toml        # Package metadata and dependencies
```

## Requirements

- Python 3.11 or newer (Python 3.13 is supported by the current environment).
- PostgreSQL with a database and user configured for the application.
- Ollama installed locally with the configured Qwen3 model, when using research or workflow extraction.
- The BGE embedding model available in the local sentence-transformers cache.
- Microsoft C++ Build Tools may be required by ChromaDB dependencies on Windows.

## Windows setup

Open PowerShell in the repository directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

If using Command Prompt instead of PowerShell:

```cmd
copy .env.example .env
```

For local ChromaDB and embedding inference, install the optional AI dependencies after the base environment works:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ai]"
```

Do not install or download models automatically during tests.

## Configuration

Copy `.env.example` to `.env` and set the local PostgreSQL connection values. Important settings include:

- `DATABASE_URL` — SQLAlchemy URL, normally `postgresql+psycopg://...`.
- `API_BASE_URL` — Streamlit-to-FastAPI URL, normally `http://127.0.0.1:8000`.
- `API_TIMEOUT_SECONDS` — frontend HTTP timeout for synchronous requests.
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_TIMEOUT_SECONDS` — local Ollama settings.
- `EMBEDDING_MODEL_NAME` — local BGE model identifier.
- `MAX_UPLOAD_SIZE_MB`, `CHUNK_SIZE`, and `CHUNK_OVERLAP` — ingestion limits.

Never commit `.env`, passwords, uploaded documents, model files, PostgreSQL data, or ChromaDB data.

## Run the application

Apply database migrations from the repository directory:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Start PostgreSQL first, then run FastAPI in one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Run Streamlit in a second terminal:

```powershell
.\.venv\Scripts\streamlit.exe run app/ui/streamlit_app.py
```

Open `http://localhost:8501`. The backend health check is available at `http://127.0.0.1:8000/health`.

## Main API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Dependency-free liveness check |
| POST | `/api/documents` | Upload, extract, embed, and index a document |
| GET | `/api/documents` | List document metadata |
| GET | `/api/documents/{document_id}` | Get document status and metadata |
| DELETE | `/api/documents/{document_id}` | Delete metadata and associated vectors |
| POST | `/api/research/answer` | Ask a question scoped to selected indexed documents |
| GET/POST | `/api/reviews` | List or create workflow reviews |
| GET | `/api/reviews/{review_id}` | Get a review and its evidence |
| POST | `/api/reviews/{review_id}/approve` | Approve a pending review |
| POST | `/api/reviews/{review_id}/reject` | Reject a pending review |

Example upload from PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/documents `
  -F "file=@.\sample.txt;type=text/plain"
```

## Testing

Run the complete suite:

```powershell
.\.venv\Scripts\pytest.exe -q --basetemp .pytest-tmp
```

The latest verified suite reported **51 passed and 1 skipped**. The skipped test is the PDF fixture in environments where PyMuPDF's native DLL is blocked. Pytest may also warn that `.pytest_cache` cannot be written on machines with restrictive folder permissions; this does not affect test execution.

The automated suite mostly uses SQLite fixtures and mocked local-AI boundaries. A previous local verification run exercised PostgreSQL, persistent ChromaDB, real BGE embeddings, Ollama/Qwen3, TXT/DOCX ingestion, research, workflow approval, and cleanup. PDF execution remains environment-dependent and was not claimed as verified in the blocked environment.

## Local AI behavior

The embedding service refuses implicit model downloads. Ollama must be running locally and the configured model must already be available. If retrieval returns no usable evidence, or the model response contains malformed or unsupported citations, the application abstains rather than inventing an answer.

## Safety and limitations

- Document contents are treated as untrusted data, not instructions.
- Research retrieval is scoped to selected indexed document IDs.
- Citations must map to retrieved chunks before an answer is returned.
- Workflow results remain pending until a human explicitly approves or rejects them.
- Processing is synchronous; long local-model requests may take minutes.
- Authentication and multi-user authorization are not implemented for production deployment.
