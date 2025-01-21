import grpc
import logging
from chirpstack_api import api
import config 
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def get_devices_as_dict():
    """
    Fetches all devices from ChirpStack using the chirpstack_api library with pagination.

    Returns:
        dict: A dictionary with device names as keys and metadata (e.g., EUID, description, profile ID) as values.
    """
    # Establish gRPC connection
    try:
        channel = grpc.insecure_channel(config.CHIRPSTACK_HOST)
        auth_token = [("authorization", "Bearer %s" % config.API_TOKEN)]
        
        # Create service stub for DeviceService
        device_service = api.DeviceServiceStub(channel=channel)
        logger.info("gRPC connection established.")
    except grpc.RpcError as e:
        logger.error(f"Error establishing gRPC connection: {e.details()}")
        logger.error(f"Status code: {e.code()}")
        return {}

    # Dictionary to store devices
    devices_dict = {}
    offset = config.OFFSET
    limit = config.LIMIT  # Number of devices to fetch per request

    try:
        while True:
            # Request device list with pagination and the application_id
            request = api.ListDevicesRequest(application_id=config.APPLICATION_ID, limit=limit, offset=offset)
            logger.info(f"Fetching devices with offset {offset} and limit {limit}")
            
            # Make gRPC call
            response = device_service.List(request, metadata=auth_token)

            # Log the response length
            logger.info(f"Response received: {len(response.result)} devices found.")

            # Process each device in the response
            for device in response.result:
                logger.info(f"Processing device: {device.name}")
                devices_dict[device.name] = {
                    "euid": device.dev_eui,
                    "description": device.description,
                    "device_profile_id": device.device_profile_id,
                    "device_profile_name": device.device_profile_name,
                    "created_at": device.created_at.ToDatetime().isoformat() if device.created_at else None,
                    "updated_at": device.updated_at.ToDatetime().isoformat() if device.updated_at else None,
                    "last_seen_at": device.last_seen_at.ToDatetime().isoformat() if device.last_seen_at else None,
                }

            # Break if fewer devices than limit are returned (end of list)
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

    except grpc.RpcError as e:
        logger.error(f"Error fetching devices: {e.details()}")
        return {}


if __name__ == "__main__":
    devices = get_devices_as_dict()
    logger.info("Devices: %s", devices)
