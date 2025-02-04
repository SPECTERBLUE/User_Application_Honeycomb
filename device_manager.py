import logging
import config
import grpc

from application_fetcher import ApplicationFetcher
from device_fetcher import DeviceFetcher
from tenant_fetcher import TenantFetcher
from codec_fetcher import CodecFetcher
from chirpstack_api import api
from rich.console import Console
from rich.table import Table

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeviceManager:
    def __init__(self):
        try:
            self.channel = grpc.insecure_channel(config.CHIRPSTACK_HOST)
            self.tenant_service_stub = api.TenantServiceStub(self.channel)
            self.application_service_stub = api.ApplicationServiceStub(self.channel)
            self.device_service_stub = api.DeviceServiceStub(self.channel)
            self.device_profile_service_stub = api.DeviceProfileServiceStub(self.channel)

            self.tenant_fetcher = TenantFetcher(self.tenant_service_stub)
            self.application_fetcher = ApplicationFetcher(self.application_service_stub)
            self.device_fetcher = DeviceFetcher(self.device_service_stub, config.AUTH_METADATA)
            self.codec_fetcher = CodecFetcher(self.device_profile_service_stub)

            self.all_devices = {}
        except Exception as e:
            logger.error(f"Failed to initialize DeviceManager: {e}", exc_info=True)

    def fetch_all_devices(self):
        """Fetch all devices dynamically and update the dictionary with proper error handling."""
        logger.info("Fetching all devices...")
        try:
            tenant_ids = self.tenant_fetcher.fetch_tenants()
            if not tenant_ids:
                logger.warning("No tenants found.")
                return

            logger.info(f"Fetched tenant IDs: {tenant_ids}")
            new_devices = {}
            
            for tenant_id in tenant_ids:
                try:
                    logger.info(f"Fetching applications for tenant ID: {tenant_id}")
                    application_ids = self.application_fetcher.fetch_applications(tenant_id)
                    
                    if not application_ids:
                        logger.warning(f"No applications found for tenant ID: {tenant_id}")
                        continue
                    
                    logger.info(f"Applications for tenant ID {tenant_id}: {application_ids}")
                    
                    for app_id in application_ids:
                        try:
                            logger.info(f"Fetching devices for application ID: {app_id}")
                            devices = self.device_fetcher.get_devices_as_dict(app_id)
                            
                            for device_name, device_data in devices.items():
                                try:
                                    device_profile_id = device_data.get("device_profile_id")
                                    if device_profile_id:
                                        codec_info = self.codec_fetcher.fetch_codec(device_profile_id)
                                        device_data.update(codec_info)
                                        logger.info(f"Updated codec information for device: {device_name}")
                                except Exception as e:
                                    logger.error(f"Error fetching codec for device {device_name}: {e}", exc_info=True)
                            
                            new_devices.update(devices)
                        except Exception as e:
                            logger.error(f"Error fetching devices for application {app_id}: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error fetching applications for tenant {tenant_id}: {e}", exc_info=True)
            
            self.all_devices = new_devices
            logger.info(f"Updated device list: {len(self.all_devices)} devices.")
        except Exception as e:
            logger.error(f"Error fetching all devices: {e}", exc_info=True)

    def get_device_list(self):
        """Return the latest device list."""
        return self.all_devices
    
    def show_device_names(self):
        """Display all device names in a formatted table."""
        console = Console()
        table = Table(title="Device List")

        table.add_column("Device Name", justify="left", style="cyan", no_wrap=True)
        table.add_column("Device Profile ID", justify="left", style="green")

        if not self.all_devices:
            console.print("[bold red]No devices found![/bold red]")
            return
        
        for device_name, device_data in self.all_devices.items():
            table.add_row(device_name, device_data.get("device_profile_id", "N/A"))

        console.print(table)

# Create a single instance of DeviceManager
device_manager = DeviceManager()


