"""
Full database reset: bootstrap schema + seed base data + simulate demo.

Runs all 3 steps in one shot for a fresh project setup.

Usage:
    .venv/bin/python scripts/reset_db.py              # full reset
    .venv/bin/python scripts/reset_db.py --skip-sim    # schema + seed only (no simulation)
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


def run_sql_file(path: Path, label: str) -> int:
    """Execute a T-SQL file split on GO batch separators."""
    from app.database import engine
    from sqlalchemy import text

    if not path.exists():
        print(f"  ✗ {label}: file not found — {path}")
        return 1

    src = path.read_text()
    batches = [b.strip() for b in re.split(r"(?im)^\s*GO\s*$", src) if b.strip()]
    print(f"\n{'='*60}")
    print(f"  Step: {label} ({len(batches)} batches)")
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


def run_simulation():
    """Run the demo simulation script."""
    print(f"\n{'='*60}")
    print(f"  Step: Simulate demo data")
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
    parser = argparse.ArgumentParser(description="Reset the parking database")
    parser.add_argument("--skip-sim", action="store_true", help="Skip demo simulation")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║         Parking System — Database Reset                 ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Step 1: Bootstrap schema
    f1 = run_sql_file(BOOTSTRAP_SQL, "Bootstrap schema (DDL)")
    if f1:
        print("\n⛔ Schema bootstrap had failures — stopping.")
        return 1

    # Step 2: Seed base data
    f2 = run_sql_file(SEED_SQL, "Seed base data (floors, slots, cameras, vehicles)")

    # Step 3: Simulate demo data
    if not args.skip_sim:
        f3 = run_simulation()
    else:
        f3 = 0
        print("\n  ⏭️  Simulation skipped (--skip-sim)")

    # Summary
    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"{'='*60}")
    steps = ["bootstrap.sql", "seed.sql"]
    if not args.skip_sim:
        steps.append("simulate_demo.py")
    print(f"  Ran: {' → '.join(steps)}")
    total_failures = f1 + f2 + f3
    if total_failures:
        print(f"  ⚠️  {total_failures} total failures")
    else:
        print(f"  ✅ All steps succeeded — database is ready")
    print(f"\n  Restart the gateway: python run.py")
    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
