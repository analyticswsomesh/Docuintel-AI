from fastapi import FastAPI

from app.api.routes.documents import router as documents_router
from app.api.routes.research import router as research_router
from app.api.routes.workflows import router as workflows_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(documents_router)
app.include_router(research_router)
app.include_router(workflows_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return a dependency-free liveness response for local development."""
    return {"status": "ok", "service": settings.app_name, "environment": settings.app_env}
