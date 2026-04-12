import asyncio
import httpx
import json

async def test_continuous_stream():
    url = "http://127.0.0.1:8001/alerts/stream"
    start_url = "http://127.0.0.1:8001/alerts/test/start?interval=0.5"
    stop_url = "http://127.0.0.1:8001/alerts/test/stop"
    
    print("Testing continuous stream connection...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Start the stream in the background
        received_events = []
        async def listen():
            try:
                async with client.stream("GET", url) as response:
                    print(f"Connected to stream. Status: {response.status_code}")
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                            if data.get("source_system") == "test_system":
                                print(f"Received continuous alert: {data.get('alert_type')}")
                                received_events.append(data)
                                if len(received_events) >= 5:
                                    return
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Stream error: {e}")

        # Task to listen
        listener = asyncio.create_task(listen())
        
        # Give it a second to connect
        await asyncio.sleep(2)
        
        # 1. Start continuous stream
        print("Starting continuous test stream...")
        await client.post(start_url)
        
        # 2. Wait to see if we get enough events
        try:
            await asyncio.wait_for(listener, timeout=10.0)
            print(f"Successfully received {len(received_events)} continuous events!")
        except asyncio.TimeoutError:
            print("Timeout: Continuous stream did not send events fast enough.")
        
        # 3. Stop continuous stream
        print("Stopping continuous test stream...")
        await client.post(stop_url)
        print("Stream stopped successfully.")

if __name__ == "__main__":
    asyncio.run(test_continuous_stream())
