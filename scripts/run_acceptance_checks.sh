#!/usr/bin/env bash
# T24 — Run the 9 acceptance checks from HIGH_SEVERITY_FIX_PLAN.md against the
# running services. Prints PASS/FAIL per check. Read-only — safe to run
# repeatedly. Requires curl + jq + sqlcmd (or psql for non-MSSQL deployments).
#
# Usage: ./run_acceptance_checks.sh [--gateway URL] [--pms-ai URL]
# Defaults: Gateway=http://localhost:8001, PMS-AI=http://localhost:8080

set -u

GATEWAY="${GATEWAY:-http://localhost:8001}"
PMS_AI="${PMS_AI:-http://localhost:8080}"
INTERNAL_TOKEN="${CAMERAS_INTERNAL_TOKEN:-}"

pass=0
fail=0
note() { printf '  %s\n' "$*"; }
ok()   { printf '  ✅ %s\n' "$*"; pass=$((pass+1)); }
err()  { printf '  ❌ %s\n' "$*"; fail=$((fail+1)); }

check() {
    echo
    echo "── $* ──"
}

# ── Check 1: dashboard.open_alerts == alerts.active_alerts ────────────────────
check "1) dashboard.open_alerts == alerts.active_alerts"
d=$(curl -fsS -m 5 "${GATEWAY}/dashboard/kpis" | jq -r '.open_alerts // empty')
a=$(curl -fsS -m 5 "${GATEWAY}/alerts/stats"   | jq -r '.active_alerts // empty')
if [ -n "${d}" ] && [ "${d}" = "${a}" ]; then ok "both = ${d}"; else err "dashboard=${d} vs alerts=${a}"; fi

# ── Check 2: vehicles list exposes current_slot_id + current_event ─────────────
check "2) vehicles[].current_slot_id and current_event populated for parked"
items=$(curl -fsS -m 5 "${GATEWAY}/vehicles/?is_currently_parked=true&page_size=5" | jq '.items')
n=$(echo "${items}" | jq 'length')
if [ "${n}" -eq 0 ]; then
    note "no currently-parked vehicles to verify; skipping"
else
    cs=$(echo "${items}" | jq '[.[].current_slot_id] | map(select(. != null)) | length')
    ev=$(echo "${items}" | jq '[.[].current_event]   | map(select(. != null)) | length')
    if [ "${cs}" -gt 0 ]; then ok "current_slot_id populated on ${cs}/${n}"; else err "current_slot_id null on all ${n}"; fi
    if [ "${ev}" -gt 0 ]; then ok "current_event populated on ${ev}/${n}";   else err "current_event null on all ${n}"; fi
fi

# ── Check 3: three-way SQL spot check (skipped — needs DB) ────────────────────
check "3) vehicles.current_slot_id == current_event.slot_id == parking_sessions.slot_id"
note "SQL-only check — run against the live DB:"
note "  SELECT v.plate_number, v.current_slot_id, ps.slot_id"
note "    FROM vehicles v JOIN parking_sessions ps ON ps.plate_number = v.plate_number"
note "    WHERE ps.status='open' AND (v.current_slot_id IS NULL OR ps.slot_id IS NULL OR v.current_slot_id != ps.slot_id);"
note "  Expected: zero rows."

# ── Check 4: alerts.slot_id non-null where context known ──────────────────────
check "4) alerts.slot_id populated on alerts with vehicle context"
total=$(curl -fsS -m 5 "${GATEWAY}/alerts/?page_size=20" | jq '[.items[] | select(.plate_number != null)] | length')
withslot=$(curl -fsS -m 5 "${GATEWAY}/alerts/?page_size=20" | jq '[.items[] | select(.plate_number != null and .slot_id != null)] | length')
if [ "${total}" -eq 0 ]; then note "no recent alerts with plate context; skipping"
elif [ "${withslot}" -gt 0 ]; then ok "${withslot}/${total} alerts with plate also have slot_id"
else err "0/${total} alerts with plate have slot_id"
fi

# ── Check 5: entry-exit/{id} surfaces slot info ────────────────────────────────
check "5) /entry-exit/{id} detail surfaces slot_id/slot_name/floor"
id=$(curl -fsS -m 5 "${GATEWAY}/entry-exit/?page_size=1" | jq -r '.items[0].id // empty')
if [ -z "${id}" ]; then note "no entry/exit events to verify; skipping"
else
    body=$(curl -fsS -m 5 "${GATEWAY}/entry-exit/${id}")
    slot_id=$(echo "${body}" | jq -r '.slot_id // empty')
    if [ -n "${slot_id}" ]; then ok "event ${id} has slot_id=${slot_id}"; else note "event ${id} has no slot (may be open + unbound)"; fi
fi

# ── Check 6: VehicleDetail flat fields ────────────────────────────────────────
check "6) GET /vehicles/{id} exposes parked_at/floor/floor_id/parking_status/last_seen_at"
vid=$(curl -fsS -m 5 "${GATEWAY}/vehicles/?is_currently_parked=true&page_size=1" | jq -r '.items[0].id // empty')
if [ -z "${vid}" ]; then note "no currently-parked vehicle; skipping"
else
    body=$(curl -fsS -m 5 "${GATEWAY}/vehicles/${vid}")
    missing=$(echo "${body}" | jq -r '[
      (if has("parked_at")       then empty else "parked_at"       end),
      (if has("parking_status")  then empty else "parking_status"  end),
      (if has("floor")           then empty else "floor"           end),
      (if has("floor_id")        then empty else "floor_id"        end),
      (if has("last_seen_at")    then empty else "last_seen_at"    end)
    ] | join(",")')
    if [ -z "${missing}" ]; then ok "all 5 flat fields present"; else err "missing: ${missing}"; fi
fi

# ── Check 7: TZ offset logged + matching ──────────────────────────────────────
check "7) Both services run with the same FACILITY_TIMEZONE_OFFSET_HOURS"
note "Read each service's startup log and confirm it printed:"
note "  Gateway: 'Facility TZ offset: UTC+<X>...'"
note "  PMS-AI:  '🕐 Facility TZ offset: UTC+<X>...'"
note "Both <X> values must match."

# ── Check 8: cameras unique names + canonical IDs ─────────────────────────────
check "8) cameras.list[].name unique and camera_id canonical (CAM-XX dash-form)"
cams=$(curl -fsS -m 5 "${GATEWAY}/cameras/?page_size=100")
total_n=$(echo "${cams}" | jq '.items | length')
uniq_n=$(echo "${cams}" | jq '.items | map(.name) | unique | length')
if [ "${total_n}" -gt 0 ] && [ "${total_n}" = "${uniq_n}" ]; then ok "${total_n} cameras, all unique names"; else err "${total_n} cameras but only ${uniq_n} unique names"; fi
nondash=$(echo "${cams}" | jq '[.items[].camera_id | select(test("^CAM-") | not)] | length')
if [ "${nondash}" -eq 0 ]; then ok "all camera_ids are dash-form"; else err "${nondash} camera_ids are NOT dash-form (expected CAM-XX)"; fi

# ── Check 9: parking_sessions.entry_snapshot_path non-null on healthy events ──
check "9) entry_snapshot_path populated on recent entries"
recent_open=$(curl -fsS -m 5 "${GATEWAY}/entry-exit/?status=open&page_size=10" | jq '[.items[] | select(.entry.snapshot_url != null)] | length')
recent_total=$(curl -fsS -m 5 "${GATEWAY}/entry-exit/?status=open&page_size=10" | jq '.items | length')
if [ "${recent_total}" -eq 0 ]; then note "no recent open events; skipping"
elif [ "${recent_open}" -gt 0 ]; then ok "${recent_open}/${recent_total} recent entries have snapshot"
else err "0/${recent_total} entries have snapshot — verify CAM-ENTRY is sending events (T22)"
fi

echo
echo "=========================================="
printf "Result: %d passed, %d failed\n" "${pass}" "${fail}"
echo "=========================================="
[ "${fail}" -eq 0 ]
