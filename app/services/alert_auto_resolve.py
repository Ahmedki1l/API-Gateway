"""Auto-resolve alerts that a vehicle-registry edit has made obsolete.

Background: the violation alerts raised upstream (VideoAnalytics / PMS-AI)
compare what the camera saw against what the registry knew *at that moment*.
When an operator later fixes the registry — gives the car the title `CEO`,
registers an unknown plate, marks a car as special-needs — the alert that was
raised is no longer a violation, but nothing clears it and it keeps the slot
red on the Occupancy map.

`auto_resolve_alerts_for_vehicle()` is called after every successful write in
`routers/vehicles.py` (POST and PUT). It re-evaluates that plate's open,
non-test alerts against the *current* registry row and resolves the ones the
edit has satisfied. Three rules, all conservative — an alert is only resolved
when the new data positively clears it:

1. **Named-slot** (`vehicle_intrusion` / legacy `named_slot_violation`) —
   resolved when `parking_slots.reserved_for` for the alert's slot now matches
   the vehicle's `title` (comparison ignores case, spaces and punctuation, so
   `"C.E.O"` clears a slot reserved for `CEO`).
2. **`unknown_vehicle`** — resolved when the plate is now `is_registered = 1`.
3. **`special_needs_violation`** — resolved when the vehicle's title marks it
   as special-needs entitled (`_SPECIAL_NEEDS_TITLES`) or matches the slot's
   `reserved_for` the same way rule 1 does.

Nothing here ever *raises* an alert, and a resolved alert is never re-opened —
if a later edit removes the title, the historical resolution stands.

Schema tolerance: `alerts.slot_id`, `alerts.resolved_by`,
`alerts.resolution_notes` and the `parking_slots.reserved_for` /
`reservation_type` columns are all probed (via `_alerts_extra_cols()` and
`_floor_schema()`) before being referenced — same contract as the routers.
"""
import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import rows

# Alert types keyed to "this car doesn't belong in this named slot". The
# legacy name survives until sql/migrate_named_slot_violation_to_vehicle_intrusion.sql
# has been run everywhere — see routers/alerts.py for the same pairing.
_NAMED_SLOT_TYPES = ("vehicle_intrusion", "named_slot_violation")

# Titles that mean "this vehicle may use a special-needs slot". Normalised
# with `_norm()` before comparison, so spacing/case/punctuation don't matter.
# Extend this set rather than the matching code when operators adopt a new label.
_SPECIAL_NEEDS_TITLES = frozenset({
    "special",
    "specialneeds",
    "disabled",
    "handicap",
    "handicapped",
    "accessible",
})

_RESOLVED_BY = "system:auto"


def _norm(value: Optional[str]) -> str:
    """Comparison key for titles / reservation labels: lowercase, with every
    non-alphanumeric character dropped. `"C.E.O "` and `"ceo"` both become
    `"ceo"`; `None` and `""` become `""` (which never matches, since callers
    guard on emptiness)."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _clears_alert(alert_type: str, title: str, reserved_for: str, is_registered: bool) -> bool:
    """The whole decision, in one place. All string args are already `_norm()`ed."""
    if alert_type in _NAMED_SLOT_TYPES:
        return bool(title) and bool(reserved_for) and title == reserved_for
    if alert_type == "unknown_vehicle":
        return is_registered
    if alert_type == "special_needs_violation":
        if title and title in _SPECIAL_NEEDS_TITLES:
            return True
        return bool(title) and bool(reserved_for) and title == reserved_for
    return False


def auto_resolve_alerts_for_vehicle(db: Session, plate_number: str) -> list[int]:
    """Resolve every open alert for `plate_number` that the registry now clears.

    Returns the ids that were resolved (empty list when nothing matched).
    Commits its own UPDATE — callers have already committed the vehicle write,
    so a failure here can't roll back the edit the operator asked for.
    """
    # Late imports: routers.alerts pulls in this module's callers, and
    # _floor_schema lives next to the router helpers. Importing at call time
    # keeps app startup free of the cycle.
    from app.routers._helpers import _floor_schema
    from app.routers.alerts import _alerts_extra_cols

    if not plate_number:
        return []

    cols = _alerts_extra_cols()
    schema = _floor_schema()

    # Pre-migration DBs keep the slot reference in `zone_id` — same fallback
    # `_alert_query_bits()` uses when `alerts.slot_id` is missing.
    slot_expr = "a.slot_id" if cols["slot_id"] else "a.zone_id"
    reserved_expr = (
        "pk.reserved_for" if schema.get("parking_slots_reserved_for") else "NULL"
    )

    candidates = rows(db, f"""
        SELECT
            a.id,
            a.alert_type,
            {reserved_expr} AS reserved_for,
            v.title         AS vehicle_title,
            v.is_registered AS vehicle_is_registered
        FROM alerts a
        LEFT JOIN parking_slots pk ON pk.slot_id = {slot_expr}
        LEFT JOIN vehicles v       ON v.plate_number = a.plate_number
        WHERE a.plate_number = :plate
          AND a.is_resolved = 0
          AND a.is_test = 0
          AND a.alert_type IN (
              'vehicle_intrusion', 'named_slot_violation',
              'unknown_vehicle', 'special_needs_violation'
          )
    """, {"plate": plate_number})

    to_resolve = [
        r["id"] for r in candidates
        if _clears_alert(
            r.get("alert_type") or "",
            _norm(r.get("vehicle_title")),
            _norm(r.get("reserved_for")),
            bool(r.get("vehicle_is_registered")),
        )
    ]
    if not to_resolve:
        return []

    audit_set = ""
    params: dict = {}
    if cols["resolved_by"]:
        audit_set += ", resolved_by = :resolved_by"
        params["resolved_by"] = _RESOLVED_BY
    if cols["resolution_notes"]:
        audit_set += ", resolution_notes = :notes"
        params["notes"] = "Auto-resolved: vehicle registry updated to match the slot reservation"

    # Named parameters can't be used for an IN list, so bind them positionally.
    id_params = {f"id{i}": aid for i, aid in enumerate(to_resolve)}
    placeholders = ", ".join(f":{k}" for k in id_params)
    params.update(id_params)

    db.execute(text(f"""
        UPDATE alerts
        SET is_resolved = 1, resolved_at = GETDATE(){audit_set}
        WHERE id IN ({placeholders}) AND is_resolved = 0
    """), params)
    db.commit()
    return to_resolve
