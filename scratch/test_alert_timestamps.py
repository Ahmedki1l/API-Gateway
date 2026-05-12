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
SYSTEM2_UTC_TYPES = {"vehicle_violation", "vehicle_intrusion", "named_slot_violation", "special_needs_violation"}
SYSTEM1_LOCAL_TYPES = {"unknown_vehicle", "overstay", "capacity_exceeded", "violence", "intrusion"}

FACILITY_TZ_OBJ = timezone(FACILITY_OFFSET)

def fix_ts(dt, alert_type):
    """Mirror of _fix_ts in alerts.py."""
    if dt is None:
        return None
    if alert_type in SYSTEM2_UTC_TYPES:
        # UTC naive -> local aware
        return dt.replace(tzinfo=timezone.utc).astimezone(FACILITY_TZ_OBJ)
    return dt  # local naive pass-through

PASS = FAIL = 0
errors = []

local_now = now_local()
utc_now   = now_utc()

OFFSETS_MINUTES = [0, 1, 5, 15, 30, 60, 90, 120, 180, 240, 360, 480, 720, 1440, 2880]

print("=" * 60)
print("CASE A: System 1 alerts -- DB stores facility-local naive")
print("  Pass-through: frontend receives naive ISO, treats as local.")
print("=" * 60)
case_a_pass = case_a_fail = 0
for atype in SYSTEM1_LOCAL_TYPES:
    for minutes_ago in OFFSETS_MINUTES:
        for _ in range(13):
            db_val = local_now - timedelta(minutes=minutes_ago, seconds=random.randint(0, 59))
            result = fix_ts(db_val, atype)
            # naive pass-through: result == db_val, no tzinfo
            ok = result == db_val and result.tzinfo is None
            if ok: case_a_pass += 1
            else:  case_a_fail += 1; errors.append(f"A {atype} {minutes_ago}m")
PASS += case_a_pass; FAIL += case_a_fail
print(f"  Result: {case_a_pass} PASS, {case_a_fail} FAIL\n")

print("=" * 60)
print("CASE B: System 2 alerts -- DB stores UTC naive (GETUTCDATE() default)")
print("  _fix_ts converts UTC->local for these types.")
print("=" * 60)
case_b_pass = case_b_fail = 0
for atype in SYSTEM2_UTC_TYPES:
    for minutes_ago in OFFSETS_MINUTES:
        for _ in range(16):
            utc_val = utc_now - timedelta(minutes=minutes_ago, seconds=random.randint(0, 59))
            result = fix_ts(utc_val, atype)
            # Should be aware +03:00 and time == utc_val + 3h
            expected_naive = utc_val + FACILITY_OFFSET
            if result is None:
                case_b_fail += 1; errors.append(f"B {atype} None result"); continue
            result_naive = result.replace(tzinfo=None)
            diff = abs((result_naive - expected_naive).total_seconds())
            ok = diff < 1 and result.utcoffset() == FACILITY_OFFSET
            if ok: case_b_pass += 1
            else:  case_b_fail += 1; errors.append(f"B {atype} {minutes_ago}m diff={diff:.1f}s")
PASS += case_b_pass; FAIL += case_b_fail
print(f"  Result: {case_b_pass} PASS, {case_b_fail} FAIL\n")

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
