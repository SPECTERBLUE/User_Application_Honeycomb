import config
from application_fetcher import ApplicationFetcher
from device_fetcher import DeviceFetcher
from chirpstack_api import api
import grpc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    Main execution function that sets up gRPC connections, fetches applications, and devices.
    """
    try:
        # Establish gRPC connection
        channel = grpc.insecure_channel(config.CHIRPSTACK_HOST)
        application_service_stub = api.ApplicationServiceStub(channel)
        device_service_stub = api.DeviceServiceStub(channel)

        logger.info("gRPC connection established.")

        # Initialize ApplicationFetcher and fetch applications
        application_fetcher = ApplicationFetcher(application_service_stub)
        application_ids = application_fetcher.fetch_applications()

        # Initialize DeviceFetcher with the required auth_token
        device_fetcher = DeviceFetcher(device_service_stub, config.AUTH_METADATA)

        # Consolidated dictionary to store devices from all applications
        all_devices = {}

        # Fetch devices for each application
        for app_id in application_ids:
            logger.info(f"Fetching devices for application ID: {app_id}")
            devices = device_fetcher.get_devices_as_dict(app_id)  # Pass app_id here

            # Check for errors or empty results
            if "error" not in devices:
                # Merge devices into all_devices dictionary
                all_devices.update(devices)
            else:
                logger.warning(f"Failed to fetch devices for application ID {app_id}: {devices}")

        # Consolidation completed; log all devices
        logger.info(f"Consolidated devices from all applications: {all_devices}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")


if __name__ == "__main__":
    main()
