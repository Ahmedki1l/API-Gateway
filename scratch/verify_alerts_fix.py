from app.database import SessionLocal
from sqlalchemy import text
import pprint

# Mock the logic for query builder
cols = {"slot_id": False, "severity": False, "location_display": False}
bits = {
    "slot_join": "LEFT JOIN parking_slots ps ON ps.slot_id = a.zone_id",
    "slot_id_expr": "ps.slot_id",
    "slot_name_expr": "COALESCE(ps.slot_name, a.slot_number)",
    "zone_id_expr": "a.zone_id",
    "zone_name_expr": "a.zone_name",
    "severity_expr": "(CASE WHEN a.alert_type IN ('violence','intrusion','vehicle_intrusion','vehicle_violation') THEN 'critical' WHEN a.alert_type IN ('unknown_vehicle','named_slot_violation','overstay','capacity_exceeded') THEN 'warning' ELSE 'info' END)",
    "location_expr": "(CASE WHEN COALESCE(ps.slot_name, a.slot_number) IS NOT NULL THEN COALESCE(ps.slot_name, a.slot_number) WHEN a.zone_name IS NOT NULL THEN a.zone_name ELSE a.camera_id END)"
}

sql = f"""
    SELECT
        a.id,
        a.alert_type,
        a.event_type,
        {bits["severity_expr"]} AS severity,
        a.plate_number,
        a.camera_id,
        {bits["slot_id_expr"]} AS slot_id,
        {bits["slot_name_expr"]} AS slot_name,
        {bits["zone_id_expr"]} AS zone_id,
        {bits["zone_name_expr"]} AS zone_name,
        a.region_id,
        a.slot_number,
        {bits["location_expr"]} AS location_display,
        a.description,
        a.snapshot_path,
        a.is_resolved,
        a.resolved_at,
        a.triggered_at
    FROM alerts a
    {bits["slot_join"]}
    LEFT JOIN vehicles v ON v.plate_number = a.plate_number
    WHERE a.is_test = 0
    ORDER BY a.triggered_at DESC
    OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY
"""

db = SessionLocal()
try:
    print("Executing query...")
    result = db.execute(text(sql))
    items = [dict(r._mapping) for r in result.fetchall()]
    print("Success! First 5 items:")
    pprint.pprint(items)
except Exception as e:
    print(f"FAILED: {e}")
finally:
    db.close()
