import asyncio
import random
import string
from itertools import cycle
from pathlib import Path
from typing import Set, List, Optional, Sequence

from app.config import facility_now_naive
from app.database import SessionLocal, rows

# Images the test stream picks its snapshot_url from, served by main.py at
# /test-alert-images. Drop more files in to widen the pool.
TEST_ALERT_IMAGES_DIR = Path(__file__).resolve().parents[2] / "static" / "test_alerts"
TEST_ALERT_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def list_test_alert_images() -> List[str]:
    if not TEST_ALERT_IMAGES_DIR.is_dir():
        return []
    return sorted(
        p.name for p in TEST_ALERT_IMAGES_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in TEST_ALERT_IMAGE_SUFFIXES
    )

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


    def start_test_stream(self, templates: List[dict], interval: float = 1.0,
                          severities: Sequence[str] = (),
                          snapshot_urls: Sequence[str] = ()):
        """Starts a background task that broadcasts random test alerts.
        `severities`, when given, are stamped on the alerts in turn, round
        and round, instead of each template's own severity. Each alert gets
        a random one of `snapshot_urls` (absolute URLs) as its snapshot."""
        levels = cycle(severities) if severities else None
        
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

                # The dbo.alert_types types that carry a plate; the rest
                # (capacity_exceeded, silent_entry) are raised without one.
                vehicle_alert_types = (
                    "unknown_vehicle", "vehicle_intrusion", "vehicle_violation",
                    "special_needs_violation", "reserved_slot_unidentified",
                )

                while True:
                    # Wait first: a restart (/test/start while running) would
                    # otherwise fire right after the old stream's last alert,
                    # two alerts in the same second.
                    await asyncio.sleep(interval)

                    template = random.choice(templates).copy()
                    if levels:
                        template["severity"] = next(levels)

                    # Basic fields
                    template["id"] = random.randint(100000, 999999)
                    template["triggered_at"] = facility_now_naive().isoformat()

                    # Always assign camera_id
                    template["camera_id"] = generate_camera_id()

                    template["snapshot_url"] = (
                        random.choice(snapshot_urls) if snapshot_urls else None
                    )

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
