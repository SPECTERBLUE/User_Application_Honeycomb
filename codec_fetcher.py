from chirpstack_api import api
import config
import logging

logger = logging.getLogger(__name__)

class CodecFetcher:
    def __init__(self, device_profile_service_stub):
        """
        Initialize CodecFetcher with a gRPC DeviceProfileServiceStub.

        Args:
            device_profile_service_stub: gRPC stub for DeviceProfileService.
        """
        self.device_profile_service_stub = device_profile_service_stub

    def fetch_codec(self, device_profile_id):
        """
        Fetch codec information for a given device profile ID.

        Args:
            device_profile_id (str): The ID of the device profile.

        Returns:
            dict: A dictionary containing codec information, or an error message.
        """
        try:
            request = api.GetDeviceProfileRequest(
                id=device_profile_id
                )
            
            logger.debug(f"Fetching device profile with ID: {device_profile_id}")
            
            if not device_profile_id:
                logger.error("Device profile ID is required but was not provided.")
                return {"error": "Invalid device profile ID"}
            
            response = self.device_profile_service_stub.Get(request, metadata=config.AUTH_METADATA)
            
             # Check if the response contains a device profile
            if not response.device_profile:
                logger.warning(f"No device profile found for ID {device_profile_id}")
                return {"error": "Device profile not found"}
            
            codec = response.device_profile.payload_codec_script if response.device_profile.payload_codec_script else None

            if codec:
                logger.info(f"Fetched codec for device profile ID {device_profile_id}: {codec}")
                return {"codec": codec}
            else:
                logger.warning(f"No codec found for device profile ID {device_profile_id}")
                return {"error": "No codec configured"}
        except Exception as e:
            logger.exception(f"Failed to fetch codec for device profile ID {device_profile_id}: {str(e)}")
            return {"error": str(e)}
