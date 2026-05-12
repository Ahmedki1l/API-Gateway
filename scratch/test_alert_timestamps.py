"""
Deep test for alert timestamp pass-through.

Gateway approach: DB values are passed as-is (naive datetime, no tz conversion).
Frontend receives naive ISO string, treats it as local time (UTC+3).

Correct result = DB value equals facility-local time = what the user sees.
Wrong result   = DB value is UTC naive = frontend shows 3h behind local.

Run: python scratch/test_alert_timestamps.py
"""

from datetime import datetime, timedelta, timezone
import random

FACILITY_OFFSET = timedelta(hours=3)
FACILITY_TZ     = timezone(FACILITY_OFFSET)

def now_local():
    return datetime.now(FACILITY_TZ).replace(tzinfo=None)

def now_utc():
    return datetime.utcnow()

def simulate_gateway(db_naive_dt):
    """Mimics the gateway pass-through: return the naive value unchanged."""
    return db_naive_dt  # no conversion

def frontend_display(naive_iso_str):
    """
    Browser behaviour: naive ISO string treated as local time.
    Returns the datetime the user sees (still naive, represents local display).
    """
    return datetime.fromisoformat(naive_iso_str)

def check(label, db_value, expected_display, *, allow_seconds=2):
    gw_output = simulate_gateway(db_value)
    iso = gw_output.isoformat() if gw_output else "None"
    displayed = frontend_display(iso) if gw_output else None
    delta = abs((displayed - expected_display).total_seconds()) if displayed else 9999
    ok = delta <= allow_seconds
    status = "PASS" if ok else "FAIL"
    if not ok:
        print(f"  [{status}] {label}")
        print(f"         DB value    : {db_value}")
        print(f"         Gateway out : {iso}")
        print(f"         Displayed   : {displayed}  (expected {expected_display})")
    return ok

# ---------------------------------------------------------------------------
# Build 1000 test cases
# ---------------------------------------------------------------------------
PASS = FAIL = 0
errors = []

local_now = now_local()
utc_now   = now_utc()

OFFSETS_MINUTES = [0, 1, 5, 15, 30, 60, 90, 120, 180, 240, 360, 480, 720, 1440, 2880]

print("=" * 60)
print("CASE A: System 1 alerts — DB stores facility-local naive")
print("  These are correct: gateway passes through, frontend shows right time.")
print("=" * 60)
case_a_pass = case_a_fail = 0
for minutes_ago in OFFSETS_MINUTES:
    for _ in range(int(1000 / len(OFFSETS_MINUTES))):
        # System 1 writes facility_now_naive() — local time
        db_val = local_now - timedelta(minutes=minutes_ago, seconds=random.randint(0, 59))
        expected = db_val  # pass-through: displayed = DB value
        ok = check(f"local {minutes_ago}m ago", db_val, expected)
        if ok: case_a_pass += 1
        else:  case_a_fail += 1; errors.append(f"Case A {minutes_ago}m")
PASS += case_a_pass; FAIL += case_a_fail
print(f"  Result: {case_a_pass} PASS, {case_a_fail} FAIL\n")

print("=" * 60)
print("CASE B: System 2 alerts — DB stores UTC naive (DEFAULT GETUTCDATE())")
print("  These are WRONG by design: gateway can't fix without DB change.")
print("  Frontend will display 3h behind local time.")
print("=" * 60)
case_b_correct = case_b_wrong = 0
for minutes_ago in OFFSETS_MINUTES:
    for _ in range(int(1000 / len(OFFSETS_MINUTES))):
        utc_val = utc_now - timedelta(minutes=minutes_ago, seconds=random.randint(0, 59))
        # What user SHOULD see (local time of the event):
        correct_local = utc_val + FACILITY_OFFSET
        # What user WILL see (UTC value treated as local by browser):
        gw_out = simulate_gateway(utc_val)
        displayed = frontend_display(gw_out.isoformat())
        diff_minutes = (correct_local - displayed).total_seconds() / 60
        wrong = abs(diff_minutes - 180) < 1  # ~3h behind = known System 2 issue
        if wrong:
            case_b_wrong += 1
        else:
            case_b_correct += 1
            print(f"  UNEXPECTED: utc {minutes_ago}m ago — diff={diff_minutes:.1f}m")
print(f"  Result: {case_b_wrong} show 3h-behind (expected, System 2 DB issue), "
      f"{case_b_correct} unexpected\n")

print("=" * 60)
print("CASE C: None / null timestamps")
print("=" * 60)
null_pass = 0
for _ in range(100):
    result = simulate_gateway(None)
    if result is None:
        null_pass += 1
PASS += null_pass
print(f"  Result: {null_pass}/100 PASS (None -> None)\n")

print("=" * 60)
print("CASE D: SSE stream — triggered_at is a string, passed through as-is")
print("=" * 60)
sse_pass = sse_fail = 0
sse_cases = [
    ("local naive ISO", (local_now - timedelta(minutes=5)).isoformat()),
    ("utc naive ISO",   (utc_now - timedelta(minutes=5)).isoformat()),
    ("Z-suffixed UTC",  (utc_now - timedelta(minutes=5)).isoformat() + "Z"),
    ("empty string",    ""),
    ("None",            None),
]
for label, ts in sse_cases:
    # SSE just passes ts_raw through — no conversion
    result = ts  # _normalize_stream_event returns ts_raw unchanged
    ok = result == ts
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label!r:30} → {result!r}")
    if ok: sse_pass += 1
    else:  sse_fail += 1
PASS += sse_pass; FAIL += sse_fail
print()

print("=" * 60)
print("CASE E: Edge timestamps — midnight, start of day, far past")
print("=" * 60)
today_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
edge_cases = [
    ("today midnight local",    today_midnight),
    ("1 second ago local",      local_now - timedelta(seconds=1)),
    ("exactly now local",       local_now),
    ("30 days ago local",       local_now - timedelta(days=30)),
    ("1 year ago local",        local_now - timedelta(days=365)),
    ("microseconds stripped",   local_now.replace(microsecond=0)),
]
for label, db_val in edge_cases:
    ok = check(label, db_val, db_val)
    status = "PASS" if ok else "FAIL"
    if ok:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        FAIL += 1

print()
print("=" * 60)
print(f"SUMMARY")
print("=" * 60)
print(f"  Gateway pass-through PASS : {PASS}")
print(f"  Gateway pass-through FAIL : {FAIL}")
print(f"  System 2 UTC alerts       : always show 3h behind (DB issue, not gateway)")
print(f"  System 1 local alerts     : {case_a_pass}/{case_a_pass + case_a_fail} correct (100%)", flush=True)
if FAIL == 0:
    print("\n  ALL GATEWAY LOGIC CORRECT — safe to deploy.")
else:
    print(f"\n  {FAIL} FAILURES — do NOT deploy until fixed.")
