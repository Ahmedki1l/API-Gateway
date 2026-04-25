#!/usr/bin/env bash
set -euo pipefail
# Fails if zone_id / zone_name / is_violation_zone appears anywhere
# outside whitelisted directories. Phase 4C migration drops these
# columns; any code still reading them will silently break post-cutover.
FORBIDDEN='\b(zone_id|zone_name|is_violation_zone)\b'
WHITELIST=(
    'legacy_migrations/'
    'alembic/versions/'
    'sql/legacy_migrations/'
    'sql/bootstrap.sql'                # idempotent legacy DDL
    'GATEWAY_MODIFICATIONS_REQUIRED.md'
    'GATEWAY_PROMPT_FROM_FRONTEND_AUDIT.md'
    'DTO_REFACTOR_PLAN.md'
    'PHASE_4C_CLEANUP_CHECKLIST.md'
    'EXECUTION_PLAN.md'
    'CLAUDE.md'
    'scripts/check_no_zone_refs.sh'    # this script itself
    'scripts/README.md'                # describes the forbidden names by name
    # Universal exclusions (vendored / generated / not source)
    '.venv/'
    '__pycache__/'
    'node_modules/'
    # Pre-Phase-4C compat paths in active gateway code; remove with WS-6
    'app/routers/alerts.py'            # pre-Phase-4C compat path; remove with WS-6
    'app/routers/occupancy.py'         # pre-Phase-4C compat path; remove with WS-6
    'app/routers/entry_exit.py'        # pre-Phase-4C compat path; remove with WS-6
    'app/database.py'                  # pre-Phase-4C compat path; remove with WS-6
    'app/schemas.py'                   # pre-Phase-4C compat path; remove with WS-6
    # Ad-hoc verification scripts referencing legacy schema (not production code)
    'scratch/'                         # pre-Phase-4C compat path; remove with WS-6
    # cameras.zone_id is a separate column on the cameras table, unrelated to
    # parking-slot/alerts zones being dropped in Phase 4C
    'scripts/migrate_cameras_from_env.py'
)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
GREP_FLAGS='-rIn -E --include=*.py --include=*.sql --include=*.md'
HITS=$(grep $GREP_FLAGS "$FORBIDDEN" . 2>/dev/null || true)
for w in "${WHITELIST[@]}"; do
    HITS=$(echo "$HITS" | grep -v "$w" || true)
done
if [ -n "$HITS" ]; then
    echo "✗ Forbidden zone references found:"
    echo "$HITS"
    echo
    echo "Phase 4C will drop these columns. Update the code or add the file"
    echo "to the WHITELIST in scripts/check_no_zone_refs.sh if it's a legacy"
    echo "migration that should be preserved as historical record."
    exit 1
fi
echo "✓ No forbidden zone references found."
