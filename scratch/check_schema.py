from app.database import SessionLocal
from sqlalchemy import text

def check_table(table_name):
    db = SessionLocal()
    try:
        res = db.execute(text(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'"))
        cols = [r[0] for r in res.fetchall()]
        print(f"Table: {table_name}")
        print(f"Columns: {cols}")
    except Exception as e:
        print(f"Error checking {table_name}: {e}")
    finally:
        db.close()

check_table('alerts')
check_table('parking_slots')
check_table('zone_occupancy')
check_table('parking_sessions')
check_table('vehicles')
