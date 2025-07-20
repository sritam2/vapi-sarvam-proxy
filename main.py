import os
import base64
import asyncio
import array
import traceback
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
from sarvamai import AsyncSarvamAI

# ────────────── Logging setup ──────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ────────────── Constants ──────────────
AUDIO_FILE_PATH = "audio-dump.raw"
SAMPLE_WIDTH = 2  # bytes (16-bit PCM)
CHANNELS = 2      # stereo
FRAME_RATE = 16000  # Hz
CHUNK_SIZE = 1280  # bytes per VAPI stereo chunk (20ms)
CHUNKS_PER_SECOND = 50
MONO_SAMPLES_PER_SECOND = FRAME_RATE

# ────────────── API Key ──────────────
load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "sk_80epfz3v_x4iYlIoDXTQyjb3NCYAXSObg")

# ────────────── FastAPI app ──────────────
app = FastAPI()

@app.websocket("/ws")
async def vapi_audio_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WebSocket] Connection accepted")

    try:
        first_message = await websocket.receive_json()
        if first_message.get("type") != "start":
            logger.warning("Invalid start message: %s", first_message)
            return

        logger.info(f"Start message received: {first_message}")
        logger.info("Expecting binary PCM audio from VAPI...")

        # Prepare audio dump and buffers
        if os.path.exists(AUDIO_FILE_PATH):
            os.remove(AUDIO_FILE_PATH)

        stereo_chunk_buffer = bytearray()
        mono_sample_buffer = array.array("h")
        chunk_count = 0
        second_count = 0

        sarvam_client = AsyncSarvamAI(api_subscription_key=SARVAM_API_KEY)

        async with sarvam_client.speech_to_text_translate_streaming.connect() as sarvam_ws:
            logger.info("[Sarvam] WebSocket connected")

            # Background task to listen to Sarvam
            async def listen_to_sarvam():
                try:
                    while True:
                        response = await sarvam_ws.recv()
                        if hasattr(response, 'data') and hasattr(response.data, 'transcript'):
                            transcript = response.data.transcript
                            if transcript:
                                logger.info(f"[Sarvam → VAPI] {transcript}")
                                await websocket.send_json({
                                    "type": "transcriber-response",
                                    "transcription": transcript,
                                    "channel": "customer"
                                })
                except Exception as e:
                    logger.error(f"[Sarvam] Listener error: {e}")
                    logger.error(traceback.format_exc())

            sarvam_listener = asyncio.create_task(listen_to_sarvam())

            with open(AUDIO_FILE_PATH, "ab") as audio_file:
                while True:
                    try:
                        message = await websocket.receive()
                        if "bytes" in message:
                            chunk_count += 1
                            stereo_chunk = message["bytes"]
                            stereo_chunk_buffer.extend(stereo_chunk)
                            audio_file.write(stereo_chunk)
                            logger.debug(f"[VAPI] Received chunk #{chunk_count} ({len(stereo_chunk)} bytes)")

                            # Convert to mono (channel 0)
                            samples = array.array("h")
                            samples.frombytes(stereo_chunk)
                            mono_samples = samples[::2]
                            mono_sample_buffer.extend(mono_samples)
                            logger.debug(f"[Mono] Buffered {len(mono_sample_buffer)} samples")

                            # Stream every ~1s
                            if len(mono_sample_buffer) >= MONO_SAMPLES_PER_SECOND:
                                second_count += 1
                                send_samples = mono_sample_buffer[:MONO_SAMPLES_PER_SECOND]
                                del mono_sample_buffer[:MONO_SAMPLES_PER_SECOND]
                                base64_chunk = base64.b64encode(send_samples.tobytes()).decode("utf-8")
                                await sarvam_ws.translate(audio=base64_chunk)
                                logger.info(f"[Sarvam] Sent 1s mono chunk #{second_count} ({len(send_samples)} samples)")
                        elif "text" in message:
                            logger.info("[WebSocket] Received text (ignored): %s", message["text"])
                    except WebSocketDisconnect:
                        logger.info("[WebSocket] Client disconnected.")
                        break
                    except Exception as e:
                        logger.error(f"[WebSocket] Unexpected error in receive loop: {e}")
                        logger.error(traceback.format_exc())
                        break

            # Flush remaining samples
            if len(mono_sample_buffer) > 0:
                base64_chunk = base64.b64encode(mono_sample_buffer.tobytes()).decode("utf-8")
                await sarvam_ws.translate(audio=base64_chunk)
                logger.info(f"[Sarvam] Flushed final mono buffer ({len(mono_sample_buffer)} samples)")

            # Send final silence
            silence = b"\x00" * MONO_SAMPLES_PER_SECOND * SAMPLE_WIDTH
            base64_silence = base64.b64encode(silence).decode("utf-8")
            await sarvam_ws.translate(audio=base64_silence)
            logger.info("[Sarvam] Sent final 1s silence")

            await asyncio.sleep(1.5)
            sarvam_listener.cancel()
            logger.info("[Sarvam] Closed listener and streaming session")

    except Exception as outer_ex:
        logger.error(f"[WebSocket] Outer exception: {outer_ex}")
        logger.error(traceback.format_exc())


@app.get("/dump")
async def download_audio():
    """Download the stored raw audio file."""
    if os.path.exists(AUDIO_FILE_PATH):
        return FileResponse(AUDIO_FILE_PATH, filename="audio-dump.raw", media_type="application/octet-stream")
    return JSONResponse(status_code=404, content={"error": "No audio file found"})
