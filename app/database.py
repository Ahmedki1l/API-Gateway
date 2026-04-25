"""SQLAlchemy session + raw-SQL helpers.

`rows()` and `scalar()` wrap `Session.execute(text(sql), params)` for the raw
text() queries used throughout the routers (SQLAlchemy ORM is not used —
the gateway is read-heavy and the SQL is more readable as text()).

Bool coercion: SQL Server's `BIT` columns come back from pyodbc/pymssql as
Python `int` (0 or 1). `rows()` post-processes each row dict and casts known
boolean column names to `bool` based on `_BOOL_COLUMNS`. **Add new boolean
columns to that frozenset when introducing them in a SELECT** — otherwise
Pydantic strict-mode (or any consumer that does `if row['is_x'] is True`)
will be surprised by the int.

This is faster than column-type introspection (which would require an extra
round-trip per query) and keeps the SQL readable.
"""
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


# Columns that are SQL Server BIT or 0/1 INT but should surface to the API as
# Python bool. Centralising this in the data-access layer means routers stop
# having to sprinkle `bool(...)` coercions everywhere.
_BOOL_COLUMNS = frozenset({
    "is_employee",
    "is_resolved",
    "is_registered",
    "is_violation_zone",
    "is_violation_slot",
    "is_available",
    "is_test",
    "is_currently_parked",
    "is_online",
    "is_alert",
    "enabled",
    "has_password",
})


def rows(db: Session, sql: str, params: dict = None) -> list[dict]:
    """Convenience helper that returns a list of dicts, with SQL bool columns coerced to Python bool."""
    result = db.execute(text(sql), params or {})
    cols = list(result.keys())
    output: list[dict] = []
    for row in result.fetchall():
        d = dict(zip(cols, row))
        for col in cols:
            if col in _BOOL_COLUMNS and d[col] is not None:
                d[col] = bool(d[col])
        output.append(d)
    return output
