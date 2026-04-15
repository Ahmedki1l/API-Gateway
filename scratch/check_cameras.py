import sys
import os

# Add app to path
sys.path.append("c:\\Users\\moham\\AI\\API Gateway")

from app.database import SessionLocal, rows

db = SessionLocal()
gates = rows(db, "SELECT DISTINCT camera_id, gate FROM entry_exit_log")
print("Unique Gates and Cameras:")
for row in gates:
    print(dict(row))

db.close()
