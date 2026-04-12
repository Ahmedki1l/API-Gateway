from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print("Checking get_slots query in occupancy.py...")
    sql = """
        SELECT
            ps.slot_id,
            ps.slot_name,
            ps.zone_id,
            ps.zone_name,
            ps.floor
        FROM parking_slots ps
        OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
    """
    db.execute(text(sql))
    print("SUCCESS (Wait, this shouldn't happen if columns are missing)")
except Exception as e:
    print(f"FAILED as expected: {e}")
finally:
    db.close()
