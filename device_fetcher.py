import logging
import config
import grpc
from chirpstack_api import api

logger = logging.getLogger(__name__)

class DeviceFetcher:
    def __init__(self, device_service_stub, auth_token):
        """
        Initializes the DeviceFetcher class.

        Args:
            device_service_stub (api.DeviceServiceStub): gRPC service stub for device operations.
            auth_token (list): gRPC authentication metadata.
        Raises:
            ValueError: If OFFSET or LIMIT are not configured in the config file.
        """
        # Log config values for debugging
        logger.info(f"Config values - LIMIT: {config.LIMIT}, OFFSET: {config.OFFSET}")

        # Validate OFFSET and LIMIT
        if config.LIMIT is None or config.OFFSET is None:
            raise ValueError("Offset and limit should be configured in the config.")
        
        self.device_service_stub = device_service_stub
        self.auth_token = auth_token
        self.offset = config.OFFSET
        self.limit = config.LIMIT
        self.max_devices = config.MAX_DEVICES

    def get_devices_as_dict(self, application_id):
        """
        Fetches all devices for a specific application ID from ChirpStack using the gRPC API with pagination.

        Args:
            application_id (str): The ID of the application for which devices should be fetched.

        Returns:
            dict: A dictionary with device names as keys and metadata as values.
            dict: Error details if fetching devices fails.
        """
        devices_dict = {}

        try:
            while True:
                # Request device list with pagination
                request = api.ListDevicesRequest(
                    application_id=application_id,
                    limit=self.limit,
                    offset=self.offset
                )
                logger.info(f"Fetching devices with offset {self.offset} and limit {self.limit}")
                
                # Make gRPC call
                response = self.device_service_stub.List(request, metadata=self.auth_token)
                logger.info(f"Response received: {len(response.result)} devices found.")

                # Process each device in the response
                for device in response.result:
                    devices_dict[device.name] = {
                        "euid": device.dev_eui,
                        "description": device.description,
                        "device_profile_id": device.device_profile_id,
                        "device_profile_name": device.device_profile_name,
                        "created_at": device.created_at.ToDatetime().isoformat() if device.created_at else None,
                        "updated_at": device.updated_at.ToDatetime().isoformat() if device.updated_at else None,
                        "last_seen_at": device.last_seen_at.ToDatetime().isoformat() if device.last_seen_at else None,
                    }

                # Check pagination limit to prevent infinite loops
                if len(response.result) < self.limit or self.offset >= self.max_devices:
                    if self.offset >= self.max_devices:
                        logger.warning("Reached maximum pagination limit.")
                    break

                # Increment offset for the next page
                self.offset += self.limit

            if not devices_dict:
                logger.warning("No devices found for the given Application ID.")
            
            return devices_dict

        except grpc.RpcError as e:
            logger.error(f"gRPC error occurred: {str(e)}")
            return {"error": "Error fetching devices", "message": str(e)}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            return {"error": "An unexpected error occurred", "message": str(e)}
