import config
import asyncio
from application_fetcher import ApplicationFetcher
from device_fetcher import DeviceFetcher
from tenant_fetcher import TenantFetcher
from codec_fetcher import CodecFetcher
from old_code.event_stream_fetcher import EventStreamFetcher
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

async def fetch_device_events(devices, event_stream_fetcher):
    """
    Asynchronously fetch event streams for multiple devices concurrently.

    Args:
        devices (dict): A dictionary of devices with `dev_eui` keys.
        event_stream_fetcher (EventStreamFetcher): The event stream fetcher instance.

    Returns:
        dict: Devices updated with their events, or `None` if no events are found.
    """
    logger.info(f"Devices structure: {devices}")  # Log the structure of devices
    tasks = []

    # Create tasks for each device
    for device_name, device_data in devices.items():  # Now iterating through items (key-value pairs)
        logger.info(f"Device name: {device_name}, Device data: {device_data}")  # Log device name and data

        # Check if device_data is a dictionary
        if isinstance(device_data, dict):
            print("device_data is a dictionary:", device_data)  # Debug statement
            dev_eui = device_data.get("euid")
            if dev_eui:
                print(f"Found dev_eui: {dev_eui}")  # Debug statement
                 # Wrap the call to handle timeout
                tasks.append(fetch_event_with_timeout(dev_eui, event_stream_fetcher))
            else:
                print("dev_eui not found in device_data")  # Debug statement
        else:
            logger.error(f"Expected dictionary but got: {type(device_data)}")

    # Gather all event streams concurrently
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error while fetching events: {str(e)}")
        return devices

    # Update devices with their corresponding events or `None` if no events
    for device_data, events in zip(devices.values(), results):
        if isinstance(events, list):  # Valid events list
            device_data["events"] = events
        elif isinstance(events, Exception):  # Handle fetch errors
            device_data["events"] = None
            logger.error(f"Error fetching event stream for DevEUI {device_data.get('euid')}: {str(events)}")
        elif events is None:  # Handle timeout (None result)
            device_data["events"] = None
            logger.warning(f"Timeout reached for DevEUI {device_data.get('euid')}. Skipping.")
        else:  # No events
            device_data["events"] = None

    return devices

async def fetch_event_with_timeout(dev_eui, event_stream_fetcher):
    """
    Wrapper for the event stream fetcher to handle timeout gracefully.
    """
    try:
        # Fetch the event stream with a timeout
        events = await event_stream_fetcher.fetch_event_stream(dev_eui)
        return events
    except Exception as e:
        # Handle any exception and propagate it back
        return e   

async def main():
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
        InternalServiceStub = api.InternalServiceStub(channel)

        logger.info("gRPC connection established.")
        
        # Initialize fetchers
        tenant_fetcher = TenantFetcher(tenant_service_stub)
        application_fetcher = ApplicationFetcher(application_service_stub)
        device_fetcher = DeviceFetcher(device_service_stub, config.AUTH_METADATA)
        codec_fetcher = CodecFetcher(device_profile_service_stub)
        event_stream_fetcher = EventStreamFetcher(InternalServiceStub)
        
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
                
                # Fetch events for devices concurrently
                devices = await fetch_device_events(devices, event_stream_fetcher)
                
                '''    
                    # Add event streams
                    dev_eui = device_data.get("euid")
                    if dev_eui:
                        events = event_stream_fetcher.fetch_event_stream(dev_eui)
                        device_data["events"] = events
                        logger.info(f"Added events for device: {device_name}")
                        '''

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
    asyncio.run(main())