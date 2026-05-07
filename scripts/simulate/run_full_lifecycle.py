#!/usr/bin/env python
"""End-to-end orchestrator for the Damanat PMS simulation suite.

Runs the full vehicle lifecycle in order:
    1. Enter garage    (01_car_enters_garage.py)
    2. Park in B1      (02_car_parks_in_slot.py)
    3. Move B1 -> B2   (04_car_moves_b1_to_b2.py)
    4. Move B2 -> B1   (05_car_moves_b2_to_b1.py)
    5. Exit garage     (06_car_exits_garage.py)

After each step the orchestrator sleeps --delay seconds, then verifies that
the leaf script's last stdout line was exactly "PASS". A single failure
stops the whole run; downstream verifications would cascade-fail otherwise.

Cleanup before/after is opt-in (default on) and uses cleanup_test_data.py
when present. If that script is missing the orchestrator emits a yellow
warning rather than failing — cleanup is best-effort.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from _common import (  # noqa: E402
    PMS_AI_DEFAULT,
    GATEWAY_DEFAULT,
    cyan,
    green,
    red,
    yellow,
)


@dataclass
class StepResult:
    label: str
    script: str
    ok: bool
    stdout: str
    duration_s: float


def run_step(label: str, script: str, args: list[str]) -> StepResult:
    """Run a single leaf simulate script. PASS = exit 0 AND last stdout line == 'PASS'."""
    cmd = [sys.executable, str(HERE / script), *args]
    cyan(f"\n--- {label} :: {script} ---")
    cyan(f"  $ {' '.join(cmd)}")
    t0 = time.monotonic()
    # Subscripts emit UTF-8 (they reconfigure stdout in _common.py); force the
    # subprocess pipe to decode UTF-8 instead of cp1252. errors="replace" keeps
    # any rogue bytes from crashing the read thread.
    proc = subprocess.run(
        cmd,
        cwd=str(HERE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    dur = time.monotonic() - t0
    sys.stdout.write(proc.stdout or "")
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    last_line = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    ok = proc.returncode == 0 and last_line == ["PASS"]
    return StepResult(
        label=label,
        script=script,
        ok=ok,
        stdout=proc.stdout,
        duration_s=dur,
    )


def run_cleanup(plate: str, pms_ai: str, gateway: str) -> None:
    """Best-effort: invoke cleanup_test_data.py if a sister agent has built it."""
    cleanup = HERE / "cleanup_test_data.py"
    if not cleanup.exists():
        yellow(f"  (cleanup_test_data.py not present at {cleanup} — skipping cleanup)")
        return
    # Derive a prefix from the plate (everything before the final dash digits).
    # Default test plate is TEST-LIFE01 -> prefix TEST-LIFE.
    prefix = plate
    while prefix and prefix[-1].isdigit():
        prefix = prefix[:-1]
    prefix = prefix.rstrip("-_") or plate
    cmd = [
        sys.executable, str(cleanup),
        "--plate-prefix", prefix,
        "--pms-ai", pms_ai,
        "--gateway", gateway,
    ]
    cyan(f"  $ {' '.join(cmd)}")
    proc = subprocess.run(
        cmd, cwd=str(HERE), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    sys.stdout.write(proc.stdout or "")
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        yellow(f"  (cleanup exited {proc.returncode} — continuing anyway)")


def main() -> int:
    p = argparse.ArgumentParser(description="Run the full PMS simulation lifecycle.")
    p.add_argument("--plate", default="TEST-LIFE01")
    p.add_argument("--cleanup-first", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--cleanup-after", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--pms-ai", default=PMS_AI_DEFAULT)
    p.add_argument("--gateway", default=GATEWAY_DEFAULT)
    p.add_argument("--delay", type=float, default=2.0)
    args = p.parse_args()

    cyan("========================================")
    cyan(f"Damanat PMS — full lifecycle for {args.plate}")
    cyan(f"  pms-ai  : {args.pms_ai}")
    cyan(f"  gateway : {args.gateway}")
    cyan(f"  delay   : {args.delay}s between steps")
    cyan("========================================")

    # Pre-flight cleanup.
    if args.cleanup_first:
        cyan("\n[pre] cleanup of stale test data...")
        run_cleanup(args.plate, args.pms_ai, args.gateway)

    # Common args every leaf script accepts.
    common = ["--pms-ai", args.pms_ai, "--gateway", args.gateway]

    # Define the lifecycle as (label, script, extra_args) tuples.
    plan: list[tuple[str, str, list[str]]] = [
        (
            "Step 1 (entry)",
            "01_car_enters_garage.py",
            ["--plate", args.plate, *common],
        ),
        (
            "Step 2 (park B1)",
            "02_car_parks_in_slot.py",
            [
                "--plate", args.plate,
                "--slot-id", "B11_CFO",
                "--zone-id", "B1-PARKING",
                "--zone-name", "B1 Parking",
                "--floor", "B1",
                *common,
            ],
        ),
        (
            "Step 3 (B1 -> B2)",
            "04_car_moves_b1_to_b2.py",
            ["--plate", args.plate, *common],
        ),
        (
            "Step 4 (B2 -> B1)",
            "05_car_moves_b2_to_b1.py",
            ["--plate", args.plate, *common],
        ),
        (
            "Step 5 (exit)",
            "06_car_exits_garage.py",
            ["--plate", args.plate, *common],
        ),
    ]

    results: list[StepResult] = []
    overall_t0 = time.monotonic()
    failed_step: StepResult | None = None

    for label, script, extra in plan:
        result = run_step(label, script, extra)
        results.append(result)
        if not result.ok:
            failed_step = result
            break
        if args.delay > 0:
            time.sleep(args.delay)

    overall_duration = time.monotonic() - overall_t0

    # Post cleanup runs even on failure (when enabled), so subsequent runs start clean.
    if args.cleanup_after:
        cyan("\n[post] cleanup of test data...")
        run_cleanup(args.plate, args.pms_ai, args.gateway)

    # ---------- Summary ----------
    cyan("\n========================================")
    cyan("Lifecycle test summary")
    cyan("========================================")

    label_w = max((len(r.label) for r in results), default=0) + 2
    for r in results:
        marker = "PASS" if r.ok else "FAIL"
        print(f"{r.label:<{label_w}}: {marker}  ({r.duration_s:.1f}s)")
    # Steps that never ran because we short-circuited.
    ran_labels = {r.label for r in results}
    for label, _script, _extra in plan:
        if label not in ran_labels:
            print(f"{label:<{label_w}}: SKIP")

    passed = sum(1 for r in results if r.ok)
    total = len(plan)

    if failed_step is None and passed == total:
        green(f"\nOverall: PASS  ({passed}/{total} steps passed in {overall_duration:.1f}s)")
        return 0

    failed = failed_step or next((r for r in results if not r.ok), None)
    if failed is not None:
        red(f"\nOverall: FAIL  ({passed}/{total} steps passed in {overall_duration:.1f}s)")
        red(f"Failing step: {failed.label}  (script: {failed.script})")
        tail = failed.stdout.strip().splitlines()[-20:]
        red("Last 20 lines of failing script's stdout:")
        red("----------------------------------------")
        for line in tail:
            print(line)
        red("----------------------------------------")
    else:
        red(f"\nOverall: FAIL  ({passed}/{total} steps passed in {overall_duration:.1f}s)")

    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        yellow("\nInterrupted.")
        sys.exit(130)
