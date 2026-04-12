from app.database import engine, text

def check_db():
    queries = {
        "tables": "SELECT name FROM sys.tables",
        "Vehicles": "SELECT TOP 0 * FROM Vehicles",
        "EntryExit": "SELECT TOP 0 * FROM EntryExit",
        "Alerts": "SELECT TOP 0 * FROM Alerts",
        "ZoneOccupancy": "SELECT TOP 0 * FROM ZoneOccupancy"
    }
    
    with engine.connect() as conn:
        for name, sql in queries.items():
            try:
                conn.execute(text(sql))
                print(f"[OK] {name}")
            except Exception as e:
                print(f"[FAIL] {name}: {e}")

if __name__ == "__main__":
    check_db()
