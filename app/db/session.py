from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Create the database engine without opening a connection immediately."""
    active_settings = settings or get_settings()
    return create_engine(active_settings.database_url, pool_pre_ping=True)


@lru_cache
def get_database_engine() -> Engine:
    """Return the process-level engine used by API dependencies."""
    return create_database_engine()


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Yield one request-scoped session for future API dependencies."""
    session = create_session_factory(get_database_engine())()
    try:
        yield session
    finally:
        session.close()
