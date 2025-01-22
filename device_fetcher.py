import logging
from chirpstack_api import api
import config

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()


class DeviceFetcher:
    """
    A class to fetch devices from ChirpStack using gRPC.
    """

    def __init__(self, device_service_stub, auth_token):
        """
        Initializes the DeviceFetcher.

        Args:
            device_service_stub: gRPC stub for DeviceService.
            auth_token: Authentication token metadata for gRPC requests.
        """
        self.device_service_stub = device_service_stub
        self.auth_token = auth_token

    def get_devices_as_dict(self):
        """
        Fetches all devices from ChirpStack using the DeviceService.

        Returns:
            dict: A dictionary with device names as keys and metadata as values.
        """
        devices_dict = {}
        offset = config.OFFSET
        limit = config.LIMIT

        try:
            while True:
                # Request device list with pagination
                request = api.ListDevicesRequest(
                    application_id=config.APPLICATION_ID, limit=limit, offset=offset
                )
                logger.info(f"Fetching devices with offset {offset} and limit {limit}")

                # Make gRPC call
                response = self.device_service_stub.List(request, metadata=self.auth_token)

                # Process each device in the response
                for device in response.result:
                    logger.info(f"Processing device: {device.name}")
                    devices_dict[device.name] = {
                        "euid": device.dev_eui,
                        "description": device.description,
                        "device_profile_id": device.device_profile_id,
                        "device_profile_name": device.device_profile_name,
                        "created_at": device.created_at.ToDatetime().isoformat()
                        if device.created_at
                        else None,
                        "updated_at": device.updated_at.ToDatetime().isoformat()
                        if device.updated_at
                        else None,
                        "last_seen_at": device.last_seen_at.ToDatetime().isoformat()
                        if device.last_seen_at
                        else None,
                    }

                # Break if fewer devices than limit are returned
                if len(response.result) < limit:
                    break

                # Increment offset for the next page
                offset += limit

                # Check if the pagination has reached the maximum limit
                if offset >= config.MAX_DEVICES:
                    logger.warning("Reached maximum pagination limit.")
                    break

            # Validate if devices were found
            if not devices_dict:
                logger.warning("No devices found for the given Application ID.")

            logger.info(f"Fetched {len(devices_dict)} devices from ChirpStack.")
            return devices_dict

        except Exception as e:
            logger.error(f"Error fetching devices: {str(e)}")
            return {}
