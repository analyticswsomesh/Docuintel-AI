# DocuIntel AI Technical Reference

This repository follows the supplied **DocuIntel AI Updated Technical Reference Report**. The complete source report is retained at `docs/DocuIntel_AI_Updated_Technical_Reference_Report.docx`; this concise working copy records its implementation decisions for day-to-day development.

## Architecture and constraints

DocuIntel AI is a modular monolith. Streamlit calls FastAPI. PostgreSQL is the authoritative store for document and workflow metadata; ChromaDB stores vectors, text, and retrieval metadata. MVP operations are synchronous with file limits and timeouts.

The application accepts text-based PDF, DOCX, and TXT files, extracts text and page/source details where available, chunks content with overlap, embeds locally, retrieves relevant passages, and asks a local Ollama-served Qwen3 candidate to answer. Answers must cite retrieved chunks and abstain when evidence is insufficient. Document text is untrusted data and must never override trusted system instructions.

## Fixed technology choices

Python 3.11+, FastAPI, Streamlit, Ollama, Qwen3 4B candidate, BAAI/bge-small-en-v1.5 candidate, ChromaDB, PostgreSQL, PyMuPDF, python-docx, Pydantic, pytest, and Docker.

Hosted AI inference/embeddings, OpenAI APIs, Celery, Redis, message brokers, OCR, and automatic consequential external actions are outside the MVP. Exact model artifacts, licenses, hardware requirements, and retrieval/answer quality must be evaluated before finalizing model setup.

## Development phases

1. Foundation and UI design system.
2. PostgreSQL metadata foundation.
3. Safe PDF/DOCX/TXT ingestion.
4. Chunking and local embeddings.
5. Persistent ChromaDB retrieval.
6. Ollama RAG with citation validation and abstention.
7. Full document workspace UI.
8. Schema-validated workflow intelligence with human review.
9. Security and reliability regression coverage.
10. Final integration, Docker packaging, and documented evidence.

## Security and reliability principles

Validate file type/content, size, and extracted text; prevent path traversal; keep secrets and private content out of logs; enforce document scope on retrieval; delete file, metadata, and vectors together; and handle empty extraction, malformed files, model outages, timeouts, and database failures clearly. Confidential multi-user deployment requires authentication, authorization, tenant isolation, retention controls, and a security review.
