import os
import logging
from typing import List
import fastapi
import requests
from dotenv import load_dotenv
import sentry_sdk
from dataclasses import dataclass
from pydantic import BaseModel
import httpx

# Load environment variables
load_dotenv()

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


@dataclass
class SecondaryInstanceInfo:
    address: str


class Message(BaseModel):
    message_text: str

if os.getenv("USE_SENTRY") == "true":
    # Sentry SDK initialization
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )


# FastAPI app initialization
app = fastapi.FastAPI()


NUMBER_OF_SECONDARIES = int(os.getenv("NUMBER_OF_SECONDARIES"))
SECONDARY_SERVICE_NAME = os.getenv("SECONDARY_SERVICE_NAME")


### Kubernetes option (in progress)
# # Environment variables # kubernetes option
# SECONDARY_SERVICE_NAME = os.getenv("SECONDARY_SERVICE_NAME", "secondary-service")
# SECONDARY_STATEFULSET = os.getenv("SECONDARY_STATEFULSET", "secondary-statefulset")

### Docker Compose option
# Location directory name - the name of the directory
# where the docker compose is located
# is used for the derivation of secondaries' addresses
PROJECT_NAME = os.getenv("PROJECT_NAME")
SECONDARY_INTERNAL_PORT = os.getenv("SECONDARY_INTERNAL_PORT", 8000)
SECONDARY_HOST_NAME_PREFIX = f"{PROJECT_NAME}-{SECONDARY_SERVICE_NAME}"

messages: List[Message] = []

@app.get("/")
async def hello_world() -> dict:
    return {"status": "success", "message": "Hello world: replicated log in master!"}

@app.get("/health")
async def health() -> dict:
    logger.info("Health check called, returning OK")
    return {"status": "success", "message": "OK"}

# will be used for future debugging and tracing (Sentry)
@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
    return division_by_zero


async def get_secondaries() -> List[SecondaryInstanceInfo]:
    secondaries: List[SecondaryInstanceInfo] = []
    for i in range(1, NUMBER_OF_SECONDARIES+1):
        logger.info(f"Getting secondary {i} address: {SECONDARY_HOST_NAME_PREFIX}-{i}")
        secondary_url = f"http://{SECONDARY_HOST_NAME_PREFIX}-{i}:{SECONDARY_INTERNAL_PORT}"
        secondary_i = SecondaryInstanceInfo(address=secondary_url)
        secondaries.append(secondary_i)
        # # # beginnings of healthcheks?
        # secondary_url_healthcheck = f"{secondary_url}/health"
        # requests.get(secondary_url)
    return secondaries


@app.get("/messages")
async def get_messages() -> List[Message]:
    logger.info("Getting messages from master")
    return messages


@app.post("/messages")
async def post_message(message: Message) -> fastapi.responses.JSONResponse:
    logger.info(f"Received message: {message}")
    logger.info("Beginning process of sending message to secondaries")
    logger.info("Getting secondaries addresses")
    secondaries: List[SecondaryInstanceInfo] = await get_secondaries()
    logger.info("Sending message to secondaries")
    # can be optimized via asyncio.gather (for a simpler version)
    # to send messages and not wait for responses to 
    # send another message to the next secondary
    # For the required direct implementation,
    # the explicit logic of async communicationwill be used.
    for secondary in secondaries:
        try:
            logger.info(f"Sending message to secondary: {secondary.address}")
            url = f"{secondary.address}/internal/messages"
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=message.model_dump())
            if response.status_code == 200 or response.status_code == 201:
                logger.info(
                    f"Message sent successfully to secondary: {secondary.address}"
                )
            else:
                logger.error(
                    f"Message not sent to secondary: {secondary.address}. "
                    f"Status code: {response.status_code}"
                )
                return fastapi.responses.JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": "Failed to send the message to secondary:"
                        " Secondary server error:"
                        f" {response.status_code}",
                    },
                )
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            logger.error(
                f"Failed to connect to secondary: {secondary.address}. Error: {e}"
            )
            return fastapi.responses.JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"Failed to connect to secondary: {secondary.address}",
                },
            )

    # ENSURE consistency on all nodes
    messages.append(message)
    return fastapi.responses.JSONResponse(
        status_code=201,
        content={"status": "success", "message": "ACK from master"},
    )
