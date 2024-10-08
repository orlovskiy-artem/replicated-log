import os
import random
import logging
import asyncio
import fastapi
from pydantic import BaseModel
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

MINIMUM_SECONDS_BETWEEN_MESSAGES = int(os.getenv("MINIMUM_SECONDS_BETWEEN_MESSAGES"))
MAXIMUM_SECONDS_BETWEEN_MESSAGES = int(os.getenv("MAXIMUM_SECONDS_BETWEEN_MESSAGES"))

# Configure logging
logger = logging.getLogger(__name__)

# Check if handlers already exist to avoid duplication
if not logger.hasHandlers():
    logger.setLevel(logging.INFO)
    
    # Set up file handler
    file_handler = logging.FileHandler("master.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

app = fastapi.FastAPI()


class Message(BaseModel):
    message_text: str


messages: list[Message] = []

@app.get("/")
async def hello_world() -> fastapi.responses.JSONResponse:
    return fastapi.responses.JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Hello world: replicated log in secondary!"
        }
    )


@app.get("/health")
async def health() -> fastapi.responses.JSONResponse:
    logger.info("Health check called, returning OK")
    return fastapi.responses.JSONResponse(
        status_code=200,
        content={"status": "success", "message": "OK"}
    )


@app.get("/messages")
async def get_messages() -> list[Message]:
    logger.info("Sending messages upon request")
    return messages


@app.post("/internal/messages")
async def post_message(message: Message) -> fastapi.responses.JSONResponse:
    logger.info(f"Received message: {message.message_text}")
    sleeping_time = random.randint(
        MINIMUM_SECONDS_BETWEEN_MESSAGES, MAXIMUM_SECONDS_BETWEEN_MESSAGES
    )
    await asyncio.sleep(sleeping_time)
    messages.append(message)
    logger.info(f"Emulated sleep on saving message: {sleeping_time}")
    logger.info("Saved the message to storage")
    return fastapi.responses.JSONResponse(
        status_code=201,
        content={"status": "success", "message": "ACK from secondary"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
