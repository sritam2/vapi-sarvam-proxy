import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import traceback
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
AUDIO_FILE_PATH = "audio-dump.raw"

# Setup
load_dotenv()
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

        # Clear old audio file if it exists
        if os.path.exists(AUDIO_FILE_PATH):
            os.remove(AUDIO_FILE_PATH)

        with open(AUDIO_FILE_PATH, "ab") as audio_file:
            while True:
                try:
                    message = await websocket.receive()
                    if "bytes" in message:
                        audio_file.write(message["bytes"])
                    elif "text" in message:
                        logger.info("[WebSocket] Text message received (ignored): %s", message["text"])
                except WebSocketDisconnect:
                    logger.info("[WebSocket] Client disconnected cleanly.")
                    break
                except RuntimeError as re:
                    logger.error(f"[WebSocket] Runtime error: {str(re)}")
                    logger.error(traceback.format_exc())
                    break
                except Exception as loop_ex:
                    logger.error(f"[WebSocket] Unexpected error inside loop: {str(loop_ex)}")
                    logger.error(traceback.format_exc())
                    break

    except Exception as outer_ex:
        logger.error(f"[WebSocket] Outer exception during initial setup: {str(outer_ex)}")
        logger.error(traceback.format_exc())


@app.get("/dump")
async def download_audio():
    """Endpoint to download the stored raw audio file."""
    if os.path.exists(AUDIO_FILE_PATH):
        return FileResponse(AUDIO_FILE_PATH, filename="audio-dump.raw", media_type="application/octet-stream")
    return JSONResponse(status_code=404, content={"error": "No audio file found"})
