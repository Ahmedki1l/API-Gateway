from app.database import SessionLocal
from sqlalchemy import text
import pprint

db = SessionLocal()
try:
    print("Verifying occupancy.py get_slots fix...")
    sql = """
        SELECT
            ps.slot_id,
            ps.slot_name,
            ps.floor,
            ps.is_available,
            ps.is_violation_zone
        FROM parking_slots ps
        ORDER BY ps.floor, ps.slot_name
        OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY
    """
    result = db.execute(text(sql))
    items = [dict(r._mapping) for r in result.fetchall()]
    print("Success! Items:")
    pprint.pprint(items)
except Exception as e:
    print(f"FAILED: {e}")
finally:
    db.close()
