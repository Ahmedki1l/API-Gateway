import asyncio
import random
from datetime import datetime
from typing import Set, List, Optional

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
            return # Already running

        async def loop():
            try:
                print(f"Bus: Starting continuous test stream ({interval}s)")
                while True:
                    template = random.choice(templates).copy()
                    template["id"] = random.randint(100000, 999999) # Mock ID for test stream
                    template["triggered_at"] = datetime.now().isoformat()
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
