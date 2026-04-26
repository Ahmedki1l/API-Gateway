"""
Full database reset — single command for a fresh project.

  1. DROP all user tables (FK-safe order)
  2. Bootstrap schema  (sql/bootstrap.sql)
  3. Seed base data    (sql/seed.sql — floors, slots, cameras, vehicles)
  4. Simulate demo     (scratch/simulate_demo.py — sessions, alerts, history)

Usage:
    .venv/bin/python scripts/reset_db.py              # full reset + demo data
    .venv/bin/python scripts/reset_db.py --skip-sim   # reset + seed only (no simulation)
"""
from __future__ import annotations

import re
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BOOTSTRAP_SQL = ROOT / "sql" / "bootstrap.sql"
SEED_SQL = ROOT / "sql" / "seed.sql"
SIMULATE_PY = ROOT / "scratch" / "simulate_demo.py"


# ── Step 1: Drop all tables ─────────────────────────────────────────────
def drop_all_tables() -> int:
    """Drop every user table in FK-safe order."""
    from app.database import engine
    from sqlalchemy import text

    print(f"\n{'='*60}")
    print(f"  Step 1: Drop all tables")
    print(f"{'='*60}")

    with engine.connect() as conn:
        # Get all user tables
        result = conn.execute(text(
            "SELECT name FROM sys.tables WHERE type = 'U' ORDER BY name"
        ))
        tables = [r[0] for r in result]

        if not tables:
            print("  No tables found — fresh database")
            return 0

        print(f"  Found {len(tables)} tables: {', '.join(tables)}")

        # Drop all FK constraints first so table order doesn't matter
        print("  Dropping foreign key constraints...")
        fk_result = conn.execute(text("""
            SELECT fk.name AS fk_name, t.name AS table_name
            FROM sys.foreign_keys fk
            JOIN sys.tables t ON fk.parent_object_id = t.object_id
        """))
        fks = [(r[0], r[1]) for r in fk_result]
        for fk_name, table_name in fks:
            try:
                conn.execute(text(f"ALTER TABLE dbo.[{table_name}] DROP CONSTRAINT [{fk_name}]"))
            except Exception:
                pass  # already dropped
        conn.commit()
        print(f"    Dropped {len(fks)} constraints")

        # Now drop all tables
        print("  Dropping tables...")
        for table in tables:
            try:
                conn.execute(text(f"DROP TABLE dbo.[{table}]"))
                print(f"    Dropped {table}")
            except Exception as e:
                print(f"    FAIL {table}: {str(e).splitlines()[0][:80]}")
        conn.commit()

    print(f"\n  ✅ All tables dropped")
    return 0


# ── Step 2 & 3: Run SQL files ───────────────────────────────────────────
def run_sql_file(path: Path, label: str, step: int) -> int:
    """Execute a T-SQL file split on GO batch separators."""
    from app.database import engine
    from sqlalchemy import text

    if not path.exists():
        print(f"  ✗ {label}: file not found — {path}")
        return 1

    src = path.read_text()
    batches = [b.strip() for b in re.split(r"(?im)^\s*GO\s*$", src) if b.strip()]
    print(f"\n{'='*60}")
    print(f"  Step {step}: {label} ({len(batches)} batches)")
    print(f"{'='*60}")

    failures = 0
    with engine.connect() as conn:
        for i, batch in enumerate(batches, 1):
            preview = batch.splitlines()[0][:72] if batch.splitlines() else ""
            try:
                conn.execute(text(batch))
                conn.commit()
                print(f"  [{i:3d}/{len(batches)}] OK   {preview}")
            except Exception as e:
                conn.rollback()
                failures += 1
                msg = str(e).splitlines()[0][:120]
                print(f"  [{i:3d}/{len(batches)}] FAIL {preview}")
                print(f"             → {msg}")

    if failures:
        print(f"\n  ⚠️  {failures} batch failures")
    else:
        print(f"\n  ✅ {label} complete")
    return failures


# ── Step 4: Simulate demo data ──────────────────────────────────────────
def run_simulation() -> int:
    """Run the demo simulation script."""
    print(f"\n{'='*60}")
    print(f"  Step 4: Simulate demo data")
    print(f"{'='*60}")

    if not SIMULATE_PY.exists():
        print(f"  ✗ Simulation script not found — {SIMULATE_PY}")
        return 1

    import importlib.util
    spec = importlib.util.spec_from_file_location("simulate_demo", SIMULATE_PY)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        print(f"\n  ✅ Simulation complete")
        return 0
    except Exception as e:
        print(f"\n  ✗ Simulation failed: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Full database reset for the parking system")
    parser.add_argument("--skip-sim", action="store_true",
                        help="Skip demo simulation (schema + seed only)")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║     Parking System — Full Database Reset                ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  1. Drop all tables                                    ║")
    print("║  2. Bootstrap schema       (sql/bootstrap.sql)         ║")
    print("║  3. Seed base data         (sql/seed.sql)              ║")
    if not args.skip_sim:
        print("║  4. Simulate demo data    (scratch/simulate_demo.py)  ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Step 1: Drop everything
    drop_all_tables()

    # Step 2: Bootstrap schema
    f2 = run_sql_file(BOOTSTRAP_SQL, "Bootstrap schema (DDL)", step=2)
    if f2:
        print("\n⛔ Schema bootstrap had failures — stopping.")
        return 1

    # Step 3: Seed base data
    f3 = run_sql_file(SEED_SQL, "Seed base data (floors, slots, cameras, vehicles)", step=3)

    # Step 4: Simulate demo data
    if not args.skip_sim:
        f4 = run_simulation()
    else:
        f4 = 0
        print("\n  ⏭️  Simulation skipped (--skip-sim)")

    # Summary
    total_failures = f2 + f3 + f4
    print(f"\n{'='*60}")
    if total_failures:
        print(f"  ⚠️  Done with {total_failures} failures")
    else:
        print(f"  ✅ Database is ready — all steps succeeded")
    print(f"{'='*60}")
    print(f"\n  Next: python run.py")
    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
