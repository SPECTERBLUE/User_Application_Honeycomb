import grpc
import logging
from chirpstack_api import api
import config
from device_fetcher import DeviceFetcher

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

def main():
    # Establish gRPC connection
    try:
        channel = grpc.insecure_channel(config.CHIRPSTACK_HOST)
        auth_token = [("authorization", f"Bearer {config.API_TOKEN}")]
        device_service_stub = api.DeviceServiceStub(channel=channel)
        logger.info("gRPC connection established.")
    except grpc.RpcError as e:
        logger.error(f"Failed to establish gRPC connection: {str(e)}")
        return
    except Exception as e:
        logger.error(f"An unexpected error occurred while connecting: {str(e)}")
        return

    # Initialize the DeviceFetcher class
    device_fetcher = DeviceFetcher(device_service_stub, auth_token)

    # Fetch devices as a dictionary
    devices = device_fetcher.get_devices_as_dict()
    if "error" in devices:
        logger.error(f"Error: {devices['error']}, Message: {devices['message']}")
    else:
        logger.info(f"Devices: {devices}")


if __name__ == "__main__":
    main()
