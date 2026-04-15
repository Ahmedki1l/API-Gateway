import warnings
from sqlalchemy import create_engine, text, exc as sa_exc
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Suppress SQLAlchemy warning about unrecognized SQL Server versions (e.g. 17.0.1000.7)
warnings.filterwarnings("ignore", category=sa_exc.SAWarning, message=".*Unrecognized server version.*")

engine = create_engine(
    settings.db_connection_string,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def scalar(db: Session, sql: str, params: dict = None) -> int | None:
    """Convenience helper for single-value queries."""
    result = db.execute(text(sql), params or {})
    return result.scalar()


def rows(db: Session, sql: str, params: dict = None) -> list[dict]:
    """Convenience helper that returns a list of dicts."""
    result = db.execute(text(sql), params or {})
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]
