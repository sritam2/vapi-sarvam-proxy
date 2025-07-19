import asyncio
import websockets
import json

# Replace with your Render WebSocket endpoint
WS_URL = "wss://sarvamstt.onrender.com/ws"

async def test_custom_transcriber():
    async with websockets.connect(WS_URL) as ws:
        print("Connected to custom transcriber WebSocket")

        # Step 1: Send "start" frame (as VAPI does)
        start_payload = {
            "type": "start",
            "encoding": "linear16",
            "container": "raw",
            "sampleRate": 16000,
            "channels": 1
        }
        await ws.send(json.dumps(start_payload))
        print("Sent start frame")

        # Step 2: Send simulated raw PCM audio bytes
        fake_pcm = b"\x00\x01\x02\x03\x04\x05" * 10  # Simulated short PCM chunk
        await ws.send(fake_pcm)
        print("Sent dummy PCM bytes")

        # Step 3: Wait for a transcript (from your FastAPI test server)
        try:
            response = await ws.recv()
            print("Received:", response)
        except Exception as e:
            print("Error receiving:", e)

# Run the test
asyncio.run(test_custom_transcriber())
