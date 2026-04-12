import asyncio
import httpx
import json

async def test_stream():
    url = "http://127.0.0.1:8001/alerts/stream"
    trigger_url = "http://127.0.0.1:8001/alerts/test"
    
    print("Testing stream connection...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Start the stream in the background
        async def listen():
            received_count = 0
            try:
                async with client.stream("GET", url) as response:
                    print(f"Connected to stream. Status: {response.status_code}")
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                            print(f"Received event: {data.get('alert_type')} from {data.get('source_system')}")
                            if data.get("source_system") == "test_system":
                                received_count += 1
                                if received_count >= 8: # templates count
                                    print("Success: All test events received!")
                                    return
            except Exception as e:
                print(f"Stream error: {e}")

        # Task to listen
        listener = asyncio.create_task(listen())
        
        # Give it a second to connect
        await asyncio.sleep(2)
        
        # Trigger the test alerts
        print("Triggering test alerts...")
        resp = await client.post(trigger_url)
        print(f"Trigger response: {resp.status_code} - {resp.json()}")
        
        # Wait for listener to finish or timeout
        try:
            await asyncio.wait_for(listener, timeout=10.0)
        except asyncio.TimeoutError:
            print("Timeout: Did not receive all events.")

if __name__ == "__main__":
    asyncio.run(test_stream())
