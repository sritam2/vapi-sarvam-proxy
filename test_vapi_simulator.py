import asyncio
import websockets
import json
import wave

async def simulate_vapi():
    uri = "wss://sarvamstt.onrender.com/ws"  # Use Render URL if deployed

    async with websockets.connect(uri) as websocket:
        # Step 1: Send initial start message like VAPI
        start_msg = {
            "type": "start",
            "encoding": "linear16",
            "container": "raw",
            "sampleRate": 16000,
            "channels": 1
        }
        await websocket.send(json.dumps(start_msg))
        print("Sent initial start message")

        # Step 2: Send dummy audio data (recorded WAV or silence)
        with wave.open("sample_16k_mono.wav", "rb") as wf:
            assert wf.getframerate() == 16000
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2  # 16-bit PCM

            chunk_size = 1280  # 40ms of audio at 16kHz mono 16-bit
            while True:
                chunk = wf.readframes(chunk_size // 2)  # 2 bytes per sample
                if not chunk:
                    break
                await websocket.send(chunk)
                await asyncio.sleep(0.04)  # Simulate real-time streaming

        print("Done streaming audio")

asyncio.run(simulate_vapi())
