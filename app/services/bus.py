import asyncio
import random
import string
from datetime import datetime
from typing import Set, List, Optional

from app.database import SessionLocal, rows

def generate_plate():
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return f"{letters}-{numbers}"

def generate_camera_id():
    return f"cam{random.randint(1,14):02d}"


class Broadcaster:
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._test_task: Optional[asyncio.Task] = None

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._subscribers.add(queue)
        print(f"Bus sub: {len(self._subscribers)} total")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            print(f"Bus unsub: {len(self._subscribers)} remains")

    async def broadcast(self, event: dict):
        if not self._subscribers:
            return
        
        # Broadcast to all active queues
        for queue in list(self._subscribers):
            try:
                await queue.put(event)
            except Exception as e:
                print(f"Bus: Broadcast error: {e}")
                self.unsubscribe(queue)


    def start_test_stream(self, templates: List[dict], interval: float = 1.0):
        """Starts a background task that broadcasts random test alerts."""
        
        if self._test_task and not self._test_task.done():
            return  # Already running

        async def loop():
            # Initial data fetch
            db = SessionLocal()
            try:
                slots = rows(db, "SELECT slot_id, slot_name, floor FROM parking_slots")
                plates = rows(db, "SELECT plate_number FROM vehicles")
            except Exception as e:
                print(f"Bus: Failed to fetch test data: {e}")
                slots = []
                plates = []
            finally:
                db.close()

            try:
                print(f"Bus: Starting continuous test stream ({interval}s) with {len(slots)} slots and {len(plates)} plates")

                vehicle_alert_types = (
                    "unknown_vehicle", "overstay", "vehicle_intrusion",
                    "vehicle_violation", "named_slot_violation",
                    "unauthorized_parking", "parking_expired"
                )

                while True:
                    template = random.choice(templates).copy()

                    # Basic fields
                    template["id"] = random.randint(100000, 999999)
                    template["triggered_at"] = datetime.now().isoformat()

                    # Always assign camera_id
                    template["camera_id"] = generate_camera_id()

                    # Inject slot data if available
                    if slots:
                        slot = random.choice(slots)
                        template.update(slot)

                    # Inject plate number
                    if template.get("alert_type") in vehicle_alert_types:
                        if plates:
                            template["plate_number"] = random.choice(plates)["plate_number"]
                        else:
                            template["plate_number"] = generate_plate()
                    else:
                        template["plate_number"] = None

                    # Broadcast
                    await self.broadcast(template)

                    await asyncio.sleep(interval)

            except asyncio.CancelledError:
                print("Bus: Continuous test stream stopped")
            except Exception as e:
                print(f"Bus: Test stream error: {e}")

        self._test_task = asyncio.create_task(loop())

    def stop_test_stream(self):
        """Stops the continuous test stream if it is running."""
        if self._test_task:
            self._test_task.cancel()
            self._test_task = None

alerts_bus = Broadcaster()
