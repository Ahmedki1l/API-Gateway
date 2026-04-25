# scripts/

Per-repo helper scripts (not part of the runtime).

## `check_no_zone_refs.sh`

Pre-flight gate that fails if `zone_id`, `zone_name`, or `is_violation_zone`
appear outside the `WHITELIST` defined inside the script. Phase 4C
(`alembic/versions/b7c8d9e0f1a2_*.py`) drops these columns; any code still
reading them will silently break post-cutover (WS-2 in `EXECUTION_PLAN.md`).

Run locally:

```bash
bash scripts/check_no_zone_refs.sh
```

Exit code `0` = clean, `1` = forbidden references found.

### Wiring into CI

Add this as a required pre-merge check in whatever CI system the repo uses
(GitHub Actions, GitLab CI, Jenkins, etc.). For GitHub Actions the step is
literally one line:

```yaml
- name: Check no zone references
  run: bash scripts/check_no_zone_refs.sh
```

Place it early in the job (before tests) so PRs that re-introduce
forbidden names fail fast. The script is idempotent and has no
dependencies beyond `bash` + `grep`.
