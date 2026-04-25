"""Run sql/bootstrap.sql against the configured DB via the gateway's engine.

T-SQL scripts use `GO` as a batch separator that pyodbc/pymssql can't parse
directly. This splits on GO at the start of a line, then executes each
batch in its own transaction. Idempotent — bootstrap.sql is safe to re-run.

Usage (from the API-Gateway dir):
    ./.venv/bin/python scratch/run_bootstrap.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SQL_PATH = ROOT / "sql" / "bootstrap.sql"


def main() -> int:
    from app.database import engine
    from sqlalchemy import text

    if not SQL_PATH.exists():
        print(f"✗ SQL file not found: {SQL_PATH}")
        return 1

    src = SQL_PATH.read_text()
    batches = [b.strip() for b in re.split(r"(?im)^\s*GO\s*$", src) if b.strip()]
    print(f"Running {SQL_PATH.name} against the gateway's DB ({len(batches)} batches)…")

    failures = 0
    with engine.connect() as conn:
        for i, batch in enumerate(batches, 1):
            preview = batch.splitlines()[0][:80] if batch.splitlines() else ""
            try:
                conn.execute(text(batch))
                conn.commit()
                print(f"  [{i:3d}/{len(batches)}] OK   :: {preview}")
            except Exception as e:
                conn.rollback()
                failures += 1
                msg = str(e).splitlines()[0][:200]
                print(f"  [{i:3d}/{len(batches)}] FAIL :: {preview}")
                print(f"             → {msg}")

    print(f"Done. {failures} batch failures of {len(batches)}.")
    print("Restart the gateway so `_floor_schema()` re-probes.")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
