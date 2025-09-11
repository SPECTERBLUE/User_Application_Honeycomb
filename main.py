import threading
import logging
import config
import grpc
import uvicorn
from scheduler import start_scheduler
from event_fetcher_parse import initialize_key_rotation, start_mqtt_client
from captcha_utils import init_redis
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Replace with actual values
channel = grpc.insecure_channel(config.CHIRPSTACK_HOST)  # Set up your gRPC channel here
auth_token = config.AUTH_METADATA  # Set your authentication token here

def run_api():
    """Function to run FastAPI server in a separate thread."""
    uvicorn.run("api_downlink:app", host="0.0.0.0", port=4567, reload=False)

def start_redis_thread():
    """Wrapper to start Redis connection check in a separate thread."""
    async def run_redis():
        await init_redis()

    # Run the async redis init in its own event loop inside a thread
    def thread_target():
        asyncio.run(run_redis())

    redis_thread = threading.Thread(target=thread_target, daemon=True)
    redis_thread.start()
    logger.info("Redis init thread started.")
    return redis_thread

if __name__ == "__main__":
    try:
        logger.info("Starting API server...")
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()

        logger.info("Starting device scheduler...")
        scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
        scheduler_thread.start()

        logger.info("Initializing key rotation...")
        key_rotation_thread = threading.Thread(target=initialize_key_rotation, args=(channel, auth_token), daemon=True)
        key_rotation_thread.start()

        logger.info("Starting MQTT event listener...")
        start_mqtt_client()  # Runs in the main thread

        logger.info("Starting Redis listener...")
        start_redis_thread() 


    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.exception(f"Unexpected error in main: {e}")
