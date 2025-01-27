import config
from application_fetcher import ApplicationFetcher
from device_fetcher import DeviceFetcher
from tenant_fetcher import TenantFetcher
from codec_fetcher import CodecFetcher
from chirpstack_api import api
import grpc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_config():
    """
    Validates the required configuration parameters.
    Raises:
        ValueError: If any required configuration is missing.
    """

    if not config.CHIRPSTACK_HOST:
        raise ValueError("CHIRPSTACK_HOST must be defined in the configuration.")
    if not config.AUTH_METADATA:
        raise ValueError("AUTH_METADATA must be defined in the configuration.")

def main():
    """
    Main execution function that sets up gRPC connections, fetches applications, and devices.
    """
    try:
        # Establish gRPC connection
        channel = grpc.insecure_channel(config.CHIRPSTACK_HOST)
        tenant_service_stub = api.TenantServiceStub(channel)
        application_service_stub = api.ApplicationServiceStub(channel)
        device_service_stub = api.DeviceServiceStub(channel)
        device_profile_service_stub = api.DeviceProfileServiceStub(channel) 

        logger.info("gRPC connection established.")
        
        # Initialize fetchers
        tenant_fetcher = TenantFetcher(tenant_service_stub)
        application_fetcher = ApplicationFetcher(application_service_stub)
        device_fetcher = DeviceFetcher(device_service_stub, config.AUTH_METADATA)
        codec_fetcher = CodecFetcher(device_profile_service_stub)
        
        # Fetch tenants
        tenant_ids = tenant_fetcher.fetch_tenants()
        if not tenant_ids:
            logger.warning("No tenants found. Exiting.")
            return 

        logger.info(f"Fetched tenant IDs: {tenant_ids}")       

        # Consolidated dictionary to store devices from all applications
        all_devices = {}
        
        # Fetch applications and devices for each tenant
        for tenant_id in tenant_ids:
            logger.info(f"Fetching applications for tenant ID: {tenant_id}")
            application_ids = application_fetcher.fetch_applications(tenant_id)

            if not application_ids:
                logger.warning(f"No applications found for tenant ID: {tenant_id}")
                continue

            logger.info(f"Applications for tenant ID {tenant_id}: {application_ids}")

            # Fetch devices for each application
            for app_id in application_ids:
                logger.info(f"Fetching devices for application ID: {app_id}")
                devices = device_fetcher.get_devices_as_dict(app_id)  # Pass app_id here
                
                # Fetch codec information for each device
                for device_name, device_data in devices.items():
                    device_profile_id = device_data.get("device_profile_id")
                    if device_profile_id:
                        codec_info = codec_fetcher.fetch_codec(device_profile_id)
                        device_data.update(codec_info)
                        logger.info(f"Updated codec information for device: {device_name}")

                # Check for errors or empty results
                if "error" not in devices:
                    # Merge devices into all_devices dictionary
                    all_devices.update(devices)
                else:
                    logger.warning(f"Failed to fetch devices for application ID {app_id}: {devices}")

        # Consolidation completed; log all devices
        logger.info(f"Consolidated devices from all tenants and applications: {all_devices}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)


if __name__ == "__main__":
    validate_config()
    main()