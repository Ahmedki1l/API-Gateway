"""Verify that every boolean SELECT column in the routers is registered in
`app.database._BOOL_COLUMNS`.

Why: SQL Server returns `BIT` columns as Python `int` (0/1). The `rows()`
helper coerces known boolean column names to `bool`. If a router introduces
a new `is_*` / `has_*` / `enabled` column in a SELECT but the dev forgets
to add it to `_BOOL_COLUMNS`, the response ships an `int` and downstream
strict consumers (Pydantic strict mode, JS strict-equality) misbehave.

Run as part of pre-commit / CI:

    python scratch/verify_bool_columns.py

Exits 0 when in sync, 1 with a list of missing column names otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Match boolean-looking column references that look like they could be SQL:
#   - bare:        `is_employee`
#   - qualified:   `v.is_employee`, `ps.is_violation_zone`
#   - aliased:     `... AS is_violation_zone`
# We require the name to either be table-qualified, or appear after AS, or
# be on its own indented line — this filters out Python local variables.
_BOOL_NAME_RE = re.compile(
    r"(?:\b[A-Za-z_]\w*\.|AS\s+|,\s+|^\s+)(is_[a-z_]+|has_[a-z_]+|enabled)\b",
    re.IGNORECASE | re.MULTILINE,
)

# These match the regex but are NOT actual SQL SELECT columns. They mostly
# come from Python identifiers, FastAPI request method calls, and bind params.
_FALSE_POSITIVES = {
    "has_password",          # alias built in Python, not a SELECT column
    "is_alert",              # SSE payload field, not a DB column
    "has_camera_id",         # local var in _camera_feeds_introspect
    "has_id",                # local var in _camera_feeds_introspect
    "is_disconnected",       # request.is_disconnected() method call
    "is_employee_raw",       # local var in _event_from_row
    "is_vz",                 # bind param :is_vz
    "is_test",               # filter alias seen in alerts.py — table column already in _BOOL_COLUMNS
    "is_emp_col",            # local variable in vehicles CSV export
}


def main() -> int:
    here = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(here))

    from app.database import _BOOL_COLUMNS

    routers_dir = here / "app" / "routers"
    if not routers_dir.exists():
        print(f"✗ routers directory not found: {routers_dir}")
        return 1

    found: set[str] = set()
    for py in sorted(routers_dir.glob("*.py")):
        text = py.read_text()
        for m in _BOOL_NAME_RE.finditer(text):
            name = m.group(1).lower()
            if name not in _FALSE_POSITIVES:
                found.add(name)

    missing = sorted(found - _BOOL_COLUMNS)
    extras = sorted(_BOOL_COLUMNS - found - _FALSE_POSITIVES)

    print(f"Found {len(found)} bool-shaped SELECT columns across routers.")
    print(f"_BOOL_COLUMNS contains {len(_BOOL_COLUMNS)} entries.")

    if missing:
        print(f"\n✗ MISSING from _BOOL_COLUMNS ({len(missing)}):")
        for m in missing:
            print(f"  - {m}")
        print("\nFix: add the names above to `_BOOL_COLUMNS` in app/database.py")
        return 1

    if extras:
        print(f"\nℹ _BOOL_COLUMNS contains entries no router currently SELECTs ({len(extras)}):")
        for e in extras:
            print(f"  - {e}")
        print("(Not a failure — could be future use or columns SELECTed elsewhere.)")

    print("\n✓ All boolean SELECT columns are registered in _BOOL_COLUMNS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
